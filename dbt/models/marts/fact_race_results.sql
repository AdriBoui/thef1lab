select
    r.session_key,
    r.meeting_key,
    r.driver_number,
    r.position,
    r.number_of_laps,
    r.dnf,
    r.dns,
    r.dsq,
    r.duration,
    r.gap_to_leader,
    coalesce(p.points, 0) as points
from {{ ref('stg_session_result') }} r
inner join {{ ref('dim_session') }} s
    on r.session_key = s.session_key
    and s.session_type = 'Race'
left join {{ ref('f1_points_system') }} p
    on r.position = p.position
    and not r.dnf
    and not r.dsq
