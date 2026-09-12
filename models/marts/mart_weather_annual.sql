{{ config(materialized='table') }}

select
    extract(year from obs_date)                       as year,
    sum(precip_in)                                    as total_precip_in,
    count(*) filter (where precip_in > 0.01)          as rain_days,
    avg(tmax_f)                                       as avg_tmax_f,
    avg(tmin_f)                                       as avg_tmin_f
from {{ ref('stg_weather') }}
group by 1
order by 1
