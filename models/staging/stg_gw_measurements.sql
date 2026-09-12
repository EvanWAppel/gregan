with source as (
    select * from {{ source('raw', 'gw_measurements') }}
)

select
    site_code,
    try_cast(left(msmt_date, 10) as date) as msmt_date,
    try_cast(gwe as double)               as gwe_ft,
    try_cast(gse_gwe as double)           as depth_to_water_ft,
    wlm_qa_desc                           as qa
from source
where try_cast(gwe as double) is not null
  and coalesce(wlm_qa_desc, 'Good') not in ('No measurement', 'Missing')
