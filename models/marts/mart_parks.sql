{{ config(materialized='table') }}

select
    name,
    park_type,
    address,
    acres,
    longitude,
    latitude,
    case
        when acres < 1 then '< 1 ac'
        when acres < 10 then '1–10 ac'
        when acres < 50 then '10–50 ac'
        else '50+ ac'
    end as size_class,
    sqrt(acres) * 40 + 60 as dot_radius
from {{ ref('stg_parks') }}
