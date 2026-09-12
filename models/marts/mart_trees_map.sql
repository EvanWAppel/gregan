{{ config(materialized='table') }}

select common_name, genus, longitude, latitude
from {{ ref('stg_trees') }}
where longitude between -117.92 and -117.80
  and latitude between 34.09 and 34.20
