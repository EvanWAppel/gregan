{{ config(materialized='table') }}

select
    date_trunc('month', obs_date) as obs_month,
    pollutant,
    avg(aqi)                      as avg_aqi,
    max(aqi)                      as max_aqi,
    count(*)                      as reading_count
from {{ ref('stg_air_quality') }}
group by 1, 2
order by 1, 2
