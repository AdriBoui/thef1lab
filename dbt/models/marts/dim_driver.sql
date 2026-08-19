with ranked as (
    select
        *,
        row_number() over (partition by driver_number order by session_key desc) as rn
    from {{ ref('stg_drivers') }}
)

select
    driver_number,
    full_name,
    broadcast_name,
    name_acronym,
    team_name,
    team_colour,
    country_code,
    headshot_url
from ranked
where rn = 1
