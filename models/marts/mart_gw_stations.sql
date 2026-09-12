{{ config(materialized='table') }}

select * from {{ ref('stg_gw_stations') }}
where latitude is not null and longitude is not null
