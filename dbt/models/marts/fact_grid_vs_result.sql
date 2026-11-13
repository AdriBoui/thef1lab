-- One row per driver per Grand Prix or Sprint: where he qualified, where he
-- actually started (grid, penalties applied) and where he finished.
--
-- Qualifying position is NOT the starting position: grid penalties (power
-- unit, gearbox, previous incidents) move drivers back and shuffle everyone
-- else. Positions gained are therefore measured from the real grid.
--
-- Each race is matched to the qualifying session of the same meeting that set
-- its grid: Qualifying -> Race (Grand Prix), Sprint Qualifying -> Sprint.

with races as (
    select
        session_key,
        meeting_key,
        session_name,
        case session_name
            when 'Race' then 'Qualifying'
            when 'Sprint' then 'Sprint Qualifying'
        end as qualifying_session_name
    from {{ ref('dim_session') }}
    where session_type = 'Race'
),

race_with_quali as (
    select
        r.session_key,
        r.meeting_key,
        r.session_name,
        q.session_key as qualifying_session_key
    from races r
    left join {{ ref('dim_session') }} q
        on q.meeting_key = r.meeting_key
        and q.session_name = r.qualifying_session_name
)

select
    f.session_key,
    f.meeting_key,
    f.session_name,
    f.driver_number,
    rq.qualifying_session_key,
    qr.position as qualifying_position,
    g.grid_position,
    f.position as finish_position,
    f.dnf,
    f.dns,
    f.dsq,
    -- > 0: started behind his qualifying position (penalty)
    g.grid_position - qr.position as grid_penalty_places,
    -- > 0: finished ahead of where he started; NULL when not classified
    g.grid_position - f.position as positions_gained
from {{ ref('fact_race_results') }} f
inner join race_with_quali rq
    on f.session_key = rq.session_key
left join {{ ref('stg_starting_grid') }} g
    on g.qualifying_session_key = rq.qualifying_session_key
    and g.driver_number = f.driver_number
left join {{ ref('stg_session_result') }} qr
    on qr.session_key = rq.qualifying_session_key
    and qr.driver_number = f.driver_number
