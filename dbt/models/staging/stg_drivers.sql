with source as (
    select * from {{ source('openf1_raw', 'raw_drivers') }}
)

select
    session_key,
    meeting_key,
    driver_number,
    broadcast_name,
    full_name,
    name_acronym,
    team_name,
    team_colour,
    first_name,
    last_name,
    country_code,
    headshot_url
from source
