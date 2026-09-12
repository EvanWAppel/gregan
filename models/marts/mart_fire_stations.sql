{{ config(materialized='table') }}

select
    name,
    address,
    longitude,
    latitude
from {{ ref('stg_fire_stations') }}
