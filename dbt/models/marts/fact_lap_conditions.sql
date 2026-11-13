-- One row per race lap, with the conditions it was actually run in: weather as
-- of that moment, and whether the lap was neutralised.
--
-- Three joins worth naming, because none of them is a plain equality:
--   * weather is an AS-OF join -- the latest reading at or before the lap
--   * safety cars come from an EVENT LOG that has to be turned into intervals
--   * both end up as interval joins, one on time, one on lap numbers

with races as (
    select session_key
    from {{ ref('dim_session') }}
    where session_type = 'Race'  -- OpenF1 tags Grands Prix and Sprints alike
),

-- A track temperature of exactly 0 means the sensor dropped out, not a frozen
-- track: the raw data has air at 33 C with the track at 0 C. Anything under 5 C
-- is the same story (one pre-season reading sits at -16.5). Sentinel values that
-- look like measurements are worse than missing ones -- they average in silently.
weather as (
    select
        w.session_key,
        w.measured_at,
        w.air_temperature,
        if(w.track_temperature < 5, null, w.track_temperature) as track_temperature,
        w.humidity,
        w.rainfall > 0 as is_wet,  -- a flag, not an amount: OpenF1 only sends 0 or 1
        lead(w.measured_at) over (
            partition by w.session_key order by w.measured_at
        ) as next_measured_at
    from {{ ref('stg_weather') }} w
    join races using (session_key)
    where w.measured_at is not null
),

-- BigQuery has no ASOF JOIN, so give every reading a validity window and the
-- as-of join becomes an ordinary interval join. Capped at 10 minutes: the raw
-- gaps run up to 78 minutes, and carrying an hour-old reading onto a lap would
-- be inventing data rather than joining it.
weather_window as (
    select
        * except (next_measured_at),
        least(coalesce(next_measured_at, timestamp_add(measured_at, interval 10 minute)),
              timestamp_add(measured_at, interval 10 minute)) as valid_until
    from weather
),

-- Race control emits EVENTS ("deployed", "in this lap"), not states. Pairing them
-- into intervals is sessionisation -- the same shape as web sessions or order
-- states.
--
-- The two regimes are paired SEPARATELY. A safety car and a virtual safety car
-- are different things, and cross-pairing them is not a rounding error: at Monza
-- the log holds a safety car at lap 3 with no ending and a VSC ending at lap 29,
-- and matching those two marks 27 racing laps as neutralised.
sc_events as (
    select
        r.session_key,
        r.lap_number,
        r.message in ('VSC DEPLOYED', 'SAFETY CAR DEPLOYED') as is_start,
        if(r.message like 'VSC%', 'VSC', 'SC') as regime
    from {{ ref('stg_race_control') }} r
    join races using (session_key)
    where r.category = 'SafetyCar' and r.lap_number is not null
),

-- 25 VSC deployments for 24 endings, 17 safety cars for 14: the log loses some
-- endings, and some races finish under neutralisation. An unmatched opening is
-- closed after 5 laps rather than left running to the flag -- an explicit
-- assumption: a safety car rarely lasts longer, and leaving it open would paint
-- half a race as neutralised on the strength of one missing message.
sc_intervals as (
    select
        s.session_key,
        s.lap_number as start_lap,
        coalesce(min(e.lap_number), s.lap_number + 5) as end_lap
    from (select * from sc_events where is_start) s
    left join (select * from sc_events where not is_start) e
           on  e.session_key = s.session_key
           and e.regime     = s.regime
           and e.lap_number >= s.lap_number
    group by 1, 2
),

-- A lap far longer than the session's own pace is not a lap time: it spans a
-- red-flag suspension or a timing gap. 80 of them across the season, up to 40
-- minutes. Flagged rather than dropped -- the lap happened, its duration is just
-- not a measurement of pace.
session_pace as (
    select session_key,
           approx_quantiles(lap_duration, 100)[offset(50)] as session_median
    from {{ ref('fact_laps') }}
    join races using (session_key)
    group by 1
),

sc_laps as (
    select distinct session_key, lap
    from sc_intervals, unnest(generate_array(start_lap, least(end_lap, 200))) as lap
),

race_laps as (
    select l.*
    from {{ ref('fact_laps') }} l
    join races using (session_key)
)

select
    l.session_key,
    l.meeting_key,
    l.driver_number,
    l.lap_number,
    l.lap_duration,
    l.date_start,
    w.air_temperature,
    w.track_temperature,
    w.humidity,
    w.is_wet,
    sc.lap is not null as under_safety_car,
    l.lap_duration > p.session_median * 3 as is_outlier_lap,
    -- How stale the weather reading was. Keeping it visible is what stops an
    -- as-of join from quietly passing off an old measurement as current.
    timestamp_diff(l.date_start, w.measured_at, second) as weather_age_seconds
from race_laps l
left join weather_window w
       on  w.session_key = l.session_key
       and l.date_start >= w.measured_at
       and l.date_start <  w.valid_until
left join sc_laps sc
       on sc.session_key = l.session_key and sc.lap = l.lap_number
join session_pace p on p.session_key = l.session_key
