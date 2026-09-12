{{ config(materialized='table') }}

with daily as (
    select obs_date, aqi_category
    from {{ ref('stg_air_quality') }}
    qualify row_number() over (partition by obs_date order by aqi desc) = 1
)

select
    aqi_category,
    count(*) as day_count,
    case aqi_category
        when 'Good' then 1
        when 'Moderate' then 2
        when 'Unhealthy for Sensitive Groups' then 3
        when 'Unhealthy' then 4
        when 'Very Unhealthy' then 5
        when 'Hazardous' then 6
    end as severity
from daily
group by 1
order by severity
