{{ config(materialized='table') }}

-- Grade distribution across all Glendora inspection activities (A/B/C).

with inspections as (
    select * from {{ ref('stg_restaurant_inspections') }}
    where grade is not null and grade <> ''
)

select
    grade,
    count(*) as inspection_count
from inspections
group by 1
order by 1
