-- Reconciliation test: every point scored by a driver must land with exactly
-- one team. The constructors' total must equal the drivers' total; any row
-- returned here fails the test.

with totals as (
    select
        (select sum(points) from {{ ref('mart_constructor_standings') }}) as team_points,
        (select sum(points) from {{ ref('fact_race_results') }}) as driver_points
)

select *
from totals
where team_points != driver_points
