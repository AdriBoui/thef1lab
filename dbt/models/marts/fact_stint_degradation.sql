-- One row per race tyre stint, with an estimate of how fast the tyre faded.
--
-- This model is an ESTIMATE, not a measurement. The slope it reports mixes real
-- tyre wear with fuel burn (which makes the car quicker and hides part of the
-- wear), traffic and track evolution. The filters below cut the noise; they do
-- not remove it, and the dashboard says so.
--
-- Scope is races and sprints only. A qualifying stint is 1 to 2 laps and has no
-- degradation to speak of; a practice stint runs on an unknown, varying fuel
-- load. Carrying those rows would mean carrying rows the model cannot speak
-- about -- a grain is a promise, not just a key.

with races as (
    select session_key
    from {{ ref('dim_session') }}
    where session_type = 'Race'  -- OpenF1 tags Grands Prix and Sprints alike
),

race_laps as (
    select l.*
    from {{ ref('fact_laps') }} l
    join races using (session_key)
),

session_pace as (
    select session_key,
           approx_quantiles(lap_duration, 100)[offset(50)] as session_median
    from race_laps
    group by session_key
),

-- A safety car is a property of the LAP, not of the driver: it slows the whole
-- field at once. So detect it across drivers rather than inside one stint. A
-- stint run mostly under a safety car has a neutralised median of its own, and
-- measuring that stint against itself would read the green laps as anomalies.
lap_field as (
    select session_key, lap_number,
           approx_quantiles(lap_duration, 100)[offset(50)] as field_median
    from race_laps
    group by session_key, lap_number
),

green_laps as (
    select l.*, f.field_median
    from race_laps l
    join lap_field f using (session_key, lap_number)
    join session_pace p using (session_key)
    where f.field_median <= p.session_median * 1.15
),

stints as (
    select s.*
    from {{ ref('fact_stints') }} s
    join races using (session_key)
    where s.lap_end is not null
      and upper(s.compound) in ('SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET')
),

-- Interval join: laps carry a lap_number, stints carry a range. The equality on
-- (session, driver) prunes to a handful of rows first, and the BETWEEN only then
-- picks that stint's laps. An inequality alone cannot be hashed, so leading with
-- the equality is what keeps this cheap.
stint_laps as (
    select
        s.session_key,
        s.meeting_key,
        s.driver_number,
        s.stint_number,
        upper(s.compound) as compound,
        s.lap_start,
        s.lap_end,
        l.lap_number,
        l.lap_duration,
        l.is_pit_out_lap,
        -- Real tyre age: a stint can start on scrubbed tyres, so the age is not
        -- the lap's rank within the stint. (The slope itself is unchanged by this
        -- offset; the age range is what makes a stint readable.)
        coalesce(s.tyre_age_at_start, 0) + (l.lap_number - s.lap_start) as tyre_age,
        -- Fuel burn and track evolution hit the whole field on the same lap, so
        -- they sit inside the field median. Subtract it and they cancel out,
        -- leaving what is specific to this car on these tyres.
        l.lap_duration - l.field_median as relative_lap_seconds
    from stints s
    join green_laps l
      on  l.session_key   = s.session_key
      and l.driver_number = s.driver_number
      and l.lap_number between s.lap_start and s.lap_end
),

-- Laps that say nothing about the tyre: leaving the pits, coming back in, and
-- the standing start.
candidate as (
    select *
    from stint_laps
    where not coalesce(is_pit_out_lap, false)
      and lap_number > 1
      and lap_number < lap_end
),

-- What the field-wide filter above cannot catch: one driver stuck in traffic or
-- running wide. The median is the reference because it is robust to them -- a
-- mean would be dragged upwards by the very laps we want to drop.
with_median as (
    select
        *,
        percentile_cont(lap_duration, 0.5) over (
            partition by session_key, driver_number, stint_number
        ) as stint_median
    from candidate
),

clean as (
    select * from with_median
    where lap_duration <= stint_median * 1.07
)

select
    session_key,
    meeting_key,
    driver_number,
    stint_number,
    compound,
    any_value(lap_start) as lap_start,
    any_value(lap_end) as lap_end,
    count(*) as clean_laps,
    min(tyre_age) as tyre_age_start,
    max(tyre_age) as tyre_age_end,
    round(min(lap_duration), 3) as best_lap_seconds,
    round(any_value(stint_median), 3) as median_lap_seconds,
    -- Least-squares slope as a plain aggregate: cov(y, x) / var(x). A linear
    -- regression per stint, no Python needed.
    -- NULL under 8 clean laps: refusing to produce a number the data cannot carry
    -- is a modelling decision, not caution. Race stints average ~17 clean laps,
    -- so 8 stays permissive while killing the stints that are all noise.
    case
        when count(*) >= 8 and var_pop(tyre_age) > 0
        then round(covar_pop(lap_duration, tyre_age) / var_pop(tyre_age), 4)
    end as degradation_s_per_lap,
    -- Same slope, fitted on the lap time relative to the field. Fuel burn and
    -- track evolution cancel, so this is the one worth reading -- but read it as
    -- degradation RELATIVE TO THE FIELD: the field median carries the average
    -- tyre wear of the moment, so it cannot measure an absolute loss.
    case
        when count(*) >= 8 and var_pop(tyre_age) > 0
        then round(covar_pop(relative_lap_seconds, tyre_age) / var_pop(tyre_age), 4)
    end as relative_degradation_s_per_lap,
    -- Pace level, not fade: how far off the field this stint ran on average.
    -- Negative = quicker than the field.
    round(avg(relative_lap_seconds), 3) as pace_vs_field_seconds
from clean
group by session_key, meeting_key, driver_number, stint_number, compound
