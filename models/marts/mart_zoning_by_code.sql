{{ config(materialized='table') }}

select
    zoning,
    max(zoning_name) as zoning_name,
    count(*)         as polygon_count
from {{ ref('stg_zoning') }}
group by 1
order by 3 desc
