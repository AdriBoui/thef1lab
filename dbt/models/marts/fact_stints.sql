-- One row per driver per tyre stint (compound and lap range).
-- Feeds the tyre-strategy chart of the dashboard.
select
    session_key,
    meeting_key,
    driver_number,
    stint_number,
    compound,
    lap_start,
    lap_end,
    tyre_age_at_start
from {{ ref('stg_stints') }}
where lap_start is not null
