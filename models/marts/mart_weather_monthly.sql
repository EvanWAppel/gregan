{{ config(materialized='table') }}

select
    extract(month from obs_date)                      as month_num,
    strftime(make_date(2000, extract(month from obs_date)::int, 1), '%b') as month_name,
    avg(precip_in)                                    as avg_precip_in,
    avg(tmax_f)                                       as avg_tmax_f,
    avg(tmin_f)                                       as avg_tmin_f
from {{ ref('stg_weather') }}
group by 1
order by 1
