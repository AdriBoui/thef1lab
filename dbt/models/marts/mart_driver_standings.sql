-- Championship standings: points per driver per race, plus a running
-- cumulative total across the season (ordered by race date). Feeds the
-- classic "championship evolution" line chart, one line per driver.

with race_points as (
    select
        r.driver_number,
        s.meeting_key,
        m.meeting_name,
        m.date_start as race_date,
        r.points
    from {{ ref('fact_race_results') }} r
    inner join {{ ref('dim_session') }} s on r.session_key = s.session_key
    inner join {{ ref('dim_meeting') }} m on s.meeting_key = m.meeting_key
)

select
    rp.driver_number,
    d.full_name as driver_name,
    d.team_name,
    rp.meeting_name,
    rp.race_date,
    rp.points,
    sum(rp.points) over (
        partition by rp.driver_number
        order by rp.race_date
        rows between unbounded preceding and current row
    ) as cumulative_points
from race_points rp
left join {{ ref('dim_driver') }} d on rp.driver_number = d.driver_number
order by rp.race_date, cumulative_points desc
