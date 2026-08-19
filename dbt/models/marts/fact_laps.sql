select
    session_key,
    meeting_key,
    driver_number,
    lap_number,
    date_start,
    duration_sector_1,
    duration_sector_2,
    duration_sector_3,
    i1_speed,
    i2_speed,
    st_speed,
    lap_duration,
    is_pit_out_lap
from {{ ref('stg_laps') }}
-- drop laps with no recorded time (formation laps, red-flag interruptions, etc.)
where lap_duration is not null
