{{ config(materialized='table') }}

select agency_label, sum(upt) as boardings
from {{ ref('stg_ntd_ridership') }}
group by 1
order by 2 desc
