{{ config(materialized='table') }}

select obs_date, discharge_cfs, gage_height_ft
from {{ ref('stg_river') }}
