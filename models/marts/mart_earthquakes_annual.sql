{{ config(materialized='table') }}

select
    extract(year from origin_time) as year,
    count(*)                       as event_count,
    max(mag)                       as max_mag,
    avg(mag)                       as avg_mag
from {{ ref('stg_earthquakes') }}
group by 1
order by 1
