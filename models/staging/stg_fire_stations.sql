-- Glendora city GIS fire stations (three LA County Fire stations).

with source as (
    select * from {{ source('raw', 'fire_stations') }}
)

select
    name                              as name,
    address                           as address,
    try_cast(longitude as double)     as longitude,
    try_cast(latitude as double)      as latitude
from source
where try_cast(latitude as double) is not null
  and try_cast(longitude as double) is not null
