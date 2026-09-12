-- CAL FIRE Fire Hazard Severity Zones intersecting the Glendora bbox.
-- SRA layer is 2007 vintage; LRA is 2011. Caption that on the page.

with source as (
    select * from {{ source('raw', 'fire_hazard_zones') }}
)

select
    try_cast(objectid as integer)     as objectid,
    responsibility                    as responsibility,
    try_cast(haz_code as integer)     as haz_code,
    haz_class                         as haz_class,
    try_cast(longitude as double)     as longitude,
    try_cast(latitude as double)      as latitude,
    rings_json                        as rings_json
from source
