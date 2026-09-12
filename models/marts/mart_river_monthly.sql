{{ config(materialized='table') }}

select
    date_trunc('month', obs_date) as month,
    avg(discharge_cfs)            as avg_cfs,
    min(discharge_cfs)            as min_cfs,
    max(discharge_cfs)            as max_cfs,
    avg(gage_height_ft)           as avg_gage_ft
from {{ ref('stg_river') }}
group by 1
order by 1
