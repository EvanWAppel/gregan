{{ config(materialized='table') }}

select ridership_month, sum(upt) as boardings
from {{ ref('stg_ntd_ridership') }}
where mode_code = 'LR'
group by 1
order by 1
