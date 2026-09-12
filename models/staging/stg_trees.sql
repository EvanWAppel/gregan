with source as (
    select * from {{ source('raw', 'trees') }}
)

select
    botanical,
    common_name,
    genus,
    dbh,
    height,
    maintenance,
    district,
    try_cast(longitude as double) as longitude,
    try_cast(latitude as double)  as latitude
from source
where botanical is not null
  and lower(trim(botanical)) not in ('vacant site', 'vacant', 'stump', 'unknown')
  and try_cast(longitude as double) is not null
  and try_cast(latitude as double) is not null
