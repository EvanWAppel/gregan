{{ config(materialized='table') }}

select
    count(*)                    as total_trees,
    count(distinct common_name) as species_count,
    count(distinct genus)       as genus_count
from {{ ref('stg_trees') }}
