-- Constructors' championship: points per team per race weekend (Grand Prix +
-- Sprint of the same meeting), plus a running cumulative total across the
-- season. Teams come from fact_race_results, which records the team a driver
-- raced for in each session, so mid-season driver moves are attributed
-- correctly.

with team_points as (
    select
        r.team_name,
        r.meeting_key,
        sum(r.points) as points,
        -- one colour per team; any_value is enough as it is constant per team
        any_value(r.team_colour) as team_colour
    from {{ ref('fact_race_results') }} r
    group by r.team_name, r.meeting_key
)

select
    tp.team_name,
    tp.team_colour,
    tp.meeting_key,
    m.meeting_name,
    m.year as season,
    m.date_start as race_date,
    tp.points,
    -- reset the running total every season
    sum(tp.points) over (
        partition by tp.team_name, m.year
        order by m.date_start
        rows between unbounded preceding and current row
    ) as cumulative_points
from team_points tp
inner join {{ ref('dim_meeting') }} m on tp.meeting_key = m.meeting_key
order by race_date, cumulative_points desc
