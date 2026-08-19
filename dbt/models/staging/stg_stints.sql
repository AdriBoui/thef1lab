with source as (
    select * from {{ source('openf1_raw', 'raw_stints') }}
)

select
    session_key,
    meeting_key,
    driver_number,
    stint_number,
    lap_start,
    lap_end,
    compound,
    tyre_age_at_start
from source
