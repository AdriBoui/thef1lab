-- Starting grid of a race, after penalties. OpenF1 keys it by the qualifying
-- session that set it, so the column is renamed to make that explicit.
-- Types are cast explicitly: raw tables use schema autodetect, which drifts
-- as soon as the API sends one unexpected value (see stg_session_result).

with source as (
    select * from {{ source('openf1_raw', 'raw_starting_grid') }}
)

select
    safe_cast(session_key as int64) as qualifying_session_key,
    safe_cast(meeting_key as int64) as meeting_key,
    safe_cast(driver_number as int64) as driver_number,
    safe_cast(position as int64) as grid_position,
    safe_cast(lap_duration as float64) as qualifying_lap_seconds
from source
