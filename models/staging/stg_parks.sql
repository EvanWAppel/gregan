with source as (
    select * from {{ source('raw', 'parks') }}
)

select
    name,
    park_type,
    address,
    try_cast(acres as double)     as acres,
    try_cast(longitude as double) as longitude,
    try_cast(latitude as double)  as latitude
from source
where try_cast(acres as double) > 0
