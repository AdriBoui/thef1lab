select
    s.session_key,
    s.meeting_key,
    s.session_name,
    s.session_type,
    s.date_start,
    s.date_end,
    s.year,
    m.circuit_short_name,
    m.country_name
from {{ ref('stg_sessions') }} s
left join {{ ref('dim_meeting') }} m using (meeting_key)
