-- USGS 11085000 San Gabriel R bl Santa Fe Dam. obs_date is an ISO timestamp.

with source as (
    select * from {{ source('raw', 'river') }}
)

select
    try_cast(left(obs_date, 10) as date) as obs_date,
    try_cast(discharge_cfs as double)    as discharge_cfs,
    try_cast(gage_height_ft as double)   as gage_height_ft
from source
where try_cast(left(obs_date, 10) as date) is not null
  and (
      try_cast(discharge_cfs as double) is not null
      or try_cast(gage_height_ft as double) is not null
  )
