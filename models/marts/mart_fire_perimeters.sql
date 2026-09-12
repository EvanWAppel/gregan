{{ config(materialized='table') }}

-- One row per historic fire perimeter that intersects Glendora. Powers the
-- wildfire map, the searchable table, and the Colby Fire callout.

select
    objectid,
    fire_name,
    year,
    agency,
    gis_acres,
    alarm_date,
    cont_date,
    cause,
    is_colby,
    longitude,
    latitude,
    rings_json
from {{ ref('stg_fire_perimeters') }}
