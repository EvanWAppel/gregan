{{ config(materialized='table') }}

-- Fires intersecting Glendora, counted by decade (YEAR_ floored to 10).

select
    (year // 10) * 10                 as decade,
    count(*)                          as fire_count,
    round(sum(gis_acres), 0)          as gis_acres
from {{ ref('stg_fire_perimeters') }}
where year is not null
group by 1
order by 1
