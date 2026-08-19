with source as (
    select * from {{ source('openf1_raw', 'raw_pit') }}
)

select
    session_key,
    meeting_key,
    driver_number,
    lap_number,
    safe_cast(date as timestamp) as pit_date,
    -- stop_duration = stationary time (pit crew performance, ~2-3s).
    -- lane_duration/pit_duration include the full pit-lane transit.
    stop_duration,
    lane_duration,
    pit_duration
from source
