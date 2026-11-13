with source as (
    select * from {{ source('openf1_raw', 'raw_session_result') }}
)

select
    session_key,
    meeting_key,
    driver_number,
    -- Raw tables are loaded with schema autodetect, so one non-numeric value
    -- from OpenF1 (e.g. 'RT') turns the whole column into STRING. Cast here so
    -- downstream models always get an integer; unclassified results become NULL.
    safe_cast(position as int64) as position,
    number_of_laps,
    dnf,
    dns,
    dsq,
    duration,
    gap_to_leader
from source
