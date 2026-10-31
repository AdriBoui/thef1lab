-- One row per driver per points-scoring session: Grand Prix and Sprint.
-- OpenF1 tags both with session_type = 'Race'; only session_name tells them
-- apart ('Race' vs 'Sprint'), and each has its own points scale.

with results as (
    select
        r.session_key,
        r.meeting_key,
        s.session_name,
        r.driver_number,
        r.position,
        r.number_of_laps,
        r.dnf,
        r.dns,
        r.dsq,
        r.duration,
        r.gap_to_leader
    from {{ ref('stg_session_result') }} r
    inner join {{ ref('dim_session') }} s
        on r.session_key = s.session_key
        and s.session_type = 'Race'
)

select
    res.*,
    coalesce(
        case when res.session_name = 'Sprint' then sp.points else gp.points end,
        0
    ) as points
from results res
left join {{ ref('f1_points_system') }} gp
    on res.position = gp.position
    and not coalesce(res.dnf, false)
    and not coalesce(res.dsq, false)
left join {{ ref('f1_sprint_points_system') }} sp
    on res.position = sp.position
    and not coalesce(res.dnf, false)
    and not coalesce(res.dsq, false)
