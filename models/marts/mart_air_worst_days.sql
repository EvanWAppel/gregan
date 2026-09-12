{{ config(materialized='table') }}

select
    obs_date,
    aqi as max_aqi,
    aqi_category,
    site,
    pollutant
from {{ ref('stg_air_quality') }}
qualify row_number() over (partition by obs_date order by aqi desc) = 1
order by max_aqi desc
limit 15
