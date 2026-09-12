{{ config(materialized='table') }}

select
    extract(year from msmt_date) as year,
    median(gwe_ft)               as median_gwe_ft,
    median(depth_to_water_ft)    as median_depth_ft,
    count(*)                     as reading_count,
    count(distinct site_code)    as station_count
from {{ ref('stg_gw_measurements') }}
where msmt_date is not null
group by 1
order by 1
