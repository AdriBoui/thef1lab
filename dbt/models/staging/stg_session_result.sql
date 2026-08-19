with source as (
    select * from {{ source('openf1_raw', 'raw_session_result') }}
)

select
    session_key,
    meeting_key,
    driver_number,
    position,
    number_of_laps,
    dnf,
    dns,
    dsq,
    duration,
    gap_to_leader
from source
