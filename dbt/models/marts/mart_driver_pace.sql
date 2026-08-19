-- Driver pace & consistency per race. Median lap time shows raw speed;
-- the standard deviation of lap times shows consistency (lower = steadier).
-- Out-laps and pit-out laps are excluded so pit cycles don't skew the pace.

with race_laps as (
    select
        l.driver_number,
        l.session_key,
        s.meeting_key,
        m.meeting_name,
        l.lap_duration
    from {{ ref('fact_laps') }} l
    inner join {{ ref('dim_session') }} s
        on l.session_key = s.session_key
        and s.session_type = 'Race'
    inner join {{ ref('dim_meeting') }} m on s.meeting_key = m.meeting_key
    where l.lap_duration is not null
      and not l.is_pit_out_lap
)

select
    rl.driver_number,
    d.full_name as driver_name,
    d.team_name,
    rl.meeting_name,
    count(*) as laps_counted,
    round(approx_quantiles(rl.lap_duration, 100)[offset(50)], 3) as median_lap_seconds,
    round(min(rl.lap_duration), 3) as fastest_lap_seconds,
    round(stddev(rl.lap_duration), 3) as lap_time_stddev
from race_laps rl
left join {{ ref('dim_driver') }} d on rl.driver_number = d.driver_number
group by rl.driver_number, d.full_name, d.team_name, rl.meeting_name
order by rl.meeting_name, median_lap_seconds
