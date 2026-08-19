-- Pit stop performance by team, across the season's races.
-- Uses stop_duration (stationary pit-crew time, ~2-3s), not the full
-- pit-lane transit. Team is taken from the driver roster of each session
-- so a mid-season team change is attributed correctly.

with race_stops as (
    select
        p.session_key,
        p.stop_duration,
        d.team_name
    from {{ ref('stg_pit') }} p
    inner join {{ ref('dim_session') }} s
        on p.session_key = s.session_key
        and s.session_type = 'Race'
    inner join {{ ref('stg_drivers') }} d
        on p.session_key = d.session_key
        and p.driver_number = d.driver_number
    where p.stop_duration is not null
)

select
    team_name,
    count(*) as pit_stop_count,
    round(avg(stop_duration), 2) as avg_stop_seconds,
    round(min(stop_duration), 2) as fastest_stop_seconds,
    round(approx_quantiles(stop_duration, 100)[offset(50)], 2) as median_stop_seconds
from race_stops
group by team_name
order by median_stop_seconds
