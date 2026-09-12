{{ config(materialized='table') }}

select
    m.site_code,
    s.well_name,
    m.msmt_date,
    m.gwe_ft,
    m.depth_to_water_ft
from {{ ref('stg_gw_measurements') }} m
left join {{ ref('stg_gw_stations') }} s using (site_code)
