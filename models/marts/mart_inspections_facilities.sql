{{ config(materialized='table') }}

-- ONE ROW PER FACILITY: the most recent inspection for each Glendora
-- establishment. Powers the page KPIs (facility count, % grade A, avg score) and
-- the facilities table. Replaces the usual point map — this feed is non-spatial,
-- so a map would require geocoding the addresses (deferred; see SOURCING.md).

with ranked as (
    select
        *,
        row_number() over (
            partition by facility_id
            order by activity_date desc nulls last
        ) as rn
    from {{ ref('stg_restaurant_inspections') }}
)

select
    facility_id,
    facility_name,
    facility_address,
    facility_zip,
    pe_description,
    activity_date as last_inspection_date,
    grade         as last_grade,
    score         as last_score
from ranked
where rn = 1
