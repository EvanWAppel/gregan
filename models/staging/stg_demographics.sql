-- Census ACS 5-year estimates for Glendora city (place 30014). One row.

with source as (
    select * from {{ source('raw', 'demographics') }}
)

select
    geoid,
    name,
    try_cast(population as bigint)         as population,
    try_cast(median_age as double)         as median_age,
    try_cast(median_hh_income as bigint)   as median_hh_income,
    try_cast(median_home_value as bigint)  as median_home_value,
    try_cast(households as bigint)         as households,
    try_cast(occupied_housing as bigint)   as occupied_housing,
    try_cast(owner_occupied as bigint)     as owner_occupied,
    try_cast(renter_occupied as bigint)    as renter_occupied,
    try_cast(edu_pop_25plus as bigint)     as edu_pop_25plus,
    try_cast(bachelors as bigint)          as bachelors,
    try_cast(masters as bigint)            as masters,
    try_cast(professional as bigint)       as professional,
    try_cast(doctorate as bigint)          as doctorate
from source
