-- CAL FIRE historic fire perimeters intersecting the Glendora bbox.
-- ONE ROW PER PERIMETER. GIS acres are the polygon's area (overlapping fires
-- double-count if summed). rings_json is the outer ring in WGS84 for the map.

with source as (
    select * from {{ source('raw', 'fire_perimeters') }}
)

select
    try_cast(objectid as integer)     as objectid,
    nullif(trim(fire_name), '')       as fire_name,
    try_cast(year as integer)         as year,
    agency                            as agency,
    try_cast(gis_acres as double)     as gis_acres,
    try_cast(alarm_date as date)      as alarm_date,
    try_cast(cont_date as date)       as cont_date,
    try_cast(cause_code as integer)   as cause_code,
    cause                             as cause,
    try_cast(is_colby as boolean)     as is_colby,
    try_cast(longitude as double)     as longitude,
    try_cast(latitude as double)      as latitude,
    rings_json                        as rings_json
from source
where try_cast(gis_acres as double) > 0
