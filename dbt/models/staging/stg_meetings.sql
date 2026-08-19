with source as (
    select * from {{ source('openf1_raw', 'raw_meetings') }}
)

select
    meeting_key,
    meeting_name,
    meeting_official_name,
    location,
    country_name,
    country_code,
    circuit_key,
    circuit_short_name,
    circuit_type,
    safe_cast(date_start as timestamp) as date_start,
    safe_cast(date_end as timestamp) as date_end,
    year,
    is_cancelled
from source
