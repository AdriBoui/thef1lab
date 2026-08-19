with source as (
    select * from {{ source('openf1_raw', 'raw_sessions') }}
)

select
    session_key,
    meeting_key,
    session_name,
    session_type,
    location,
    country_name,
    circuit_short_name,
    safe_cast(date_start as timestamp) as date_start,
    safe_cast(date_end as timestamp) as date_end,
    gmt_offset,
    year
from source
