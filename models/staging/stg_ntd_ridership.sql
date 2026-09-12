with source as (
    select * from {{ source('raw', 'ntd_ridership') }}
)

select
    agency,
    agency_label,
    mode                                     as mode_code,
    mode_label,
    cast(try_cast(date as timestamp) as date) as ridership_month,
    try_cast(upt as bigint)                  as upt
from source
where try_cast(upt as bigint) is not null
