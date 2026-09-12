with source as (
    select * from {{ source('raw', 'crime') }}
)

select
    try_cast("Year" as integer)            as year,
    try_cast("Violent_sum" as integer)     as violent,
    try_cast("Property_sum" as integer)    as property,
    try_cast("Homicide_sum" as integer)    as homicide,
    try_cast("ForRape_sum" as integer)     as rape,
    try_cast("Robbery_sum" as integer)     as robbery,
    try_cast("AggAssault_sum" as integer)  as aggravated_assault,
    try_cast("Burglary_sum" as integer)    as burglary,
    try_cast("VehicleTheft_sum" as integer) as vehicle_theft,
    try_cast("LTtotal_sum" as integer)     as larceny
from source
where try_cast("Year" as integer) >= 2000
