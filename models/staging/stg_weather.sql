-- NOAA GHCN-Daily at San Gabriel Dam (USC00047779).
-- PRCP/TMAX/TMIN are tenths; SNOW/SNWD are whole mm.

with source as (
    select * from {{ source('raw', 'weather') }}
)

select
    try_cast("DATE" as date)                            as obs_date,
    try_cast(trim("PRCP") as double) / 10.0             as precip_mm,
    try_cast(trim("PRCP") as double) / 10.0 / 25.4      as precip_in,
    try_cast(trim("SNOW") as double)                    as snow_mm,
    try_cast(trim("TMAX") as double) / 10.0             as tmax_c,
    try_cast(trim("TMIN") as double) / 10.0             as tmin_c,
    try_cast(trim("TMAX") as double) / 10.0 * 9 / 5 + 32 as tmax_f,
    try_cast(trim("TMIN") as double) / 10.0 * 9 / 5 + 32 as tmin_f
from source
where try_cast("DATE" as date) is not null
