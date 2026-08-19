with source as (
    select * from {{ source('openf1_raw', 'raw_laps') }}
)

select
    session_key,
    meeting_key,
    driver_number,
    lap_number,
    safe_cast(date_start as timestamp) as date_start,
    duration_sector_1,
    duration_sector_2,
    duration_sector_3,
    i1_speed,
    i2_speed,
    st_speed,
    lap_duration,
    is_pit_out_lap
from source
