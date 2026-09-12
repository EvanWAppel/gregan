with source as (
    select * from {{ source('raw', 'zoning') }}
)

select
    zoning,
    zoning_name,
    overlay,
    try_cast(longitude as double) as longitude,
    try_cast(latitude as double)  as latitude,
    rings_json
from source
where zoning is not null and trim(zoning) <> ''
