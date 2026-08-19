with source as (
    select * from {{ source('openf1_raw', 'raw_weather') }}
)

select
    session_key,
    meeting_key,
    safe_cast(date as timestamp) as measured_at,
    air_temperature,
    track_temperature,
    humidity,
    pressure,
    rainfall,
    wind_direction,
    wind_speed
from source
