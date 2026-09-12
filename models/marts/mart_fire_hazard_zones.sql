{{ config(materialized='table') }}

select
    objectid,
    responsibility,
    haz_code,
    haz_class,
    longitude,
    latitude,
    rings_json
from {{ ref('stg_fire_hazard_zones') }}
