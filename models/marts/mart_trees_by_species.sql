{{ config(materialized='table') }}

select
    common_name,
    max(botanical) as botanical,
    count(*)       as tree_count
from {{ ref('stg_trees') }}
where common_name is not null
group by 1
order by 3 desc
