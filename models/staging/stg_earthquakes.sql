with source as (
    select * from {{ source('raw', 'earthquakes') }}
)

select
    event_id,
    try_cast(event_time_ms as bigint) as event_time_ms,
    epoch_ms(try_cast(event_time_ms as bigint)) as origin_time,
    place,
    try_cast(mag as double)           as mag,
    try_cast(longitude as double)     as longitude,
    try_cast(latitude as double)      as latitude,
    try_cast(depth_km as double)      as depth_km
from source
where event_id is not null
  and try_cast(mag as double) is not null
