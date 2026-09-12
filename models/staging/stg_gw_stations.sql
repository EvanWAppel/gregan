with source as (
    select * from {{ source('raw', 'gw_stations') }}
)

select
    site_code,
    well_name,
    try_cast(latitude as double)   as latitude,
    try_cast(longitude as double)  as longitude,
    try_cast(gse as double)        as gse_ft,
    try_cast(well_depth as double) as well_depth_ft,
    well_use,
    well_type,
    county_name,
    basin_name,
    basin_code
from source
where site_code is not null
