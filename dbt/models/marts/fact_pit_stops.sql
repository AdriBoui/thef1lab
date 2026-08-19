select
    session_key,
    meeting_key,
    driver_number,
    lap_number,
    pit_date,
    stop_duration,
    lane_duration,
    pit_duration
from {{ ref('stg_pit') }}
