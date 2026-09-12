{{ config(materialized='table') }}

select
    site_num,
    site,
    county,
    avg(latitude)   as latitude,
    avg(longitude)  as longitude,
    round(avg(aqi)) as avg_aqi,
    max(aqi)        as max_aqi,
    count(*)        as day_count
from {{ ref('stg_air_quality') }}
group by 1, 2, 3
