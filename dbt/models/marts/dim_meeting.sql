select
    meeting_key,
    meeting_name,
    meeting_official_name,
    location,
    country_name,
    country_code,
    circuit_key,
    circuit_short_name,
    circuit_type,
    date_start,
    date_end,
    year,
    -- Keep cancelled meetings in the dimension so every session/lap/pit
    -- fact still resolves to a meeting (referential integrity). OpenF1
    -- flags some 2026 events as cancelled while still exposing their
    -- sessions and data, so consumers filter on this column instead.
    is_cancelled
from {{ ref('stg_meetings') }}
