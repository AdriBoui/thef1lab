with source as (
    select * from {{ source('openf1_raw', 'raw_race_control') }}
)

select
    session_key,
    meeting_key,
    safe_cast(date as timestamp) as event_date,
    driver_number,
    lap_number,
    category,
    flag,
    scope,
    sector,
    message
from source
