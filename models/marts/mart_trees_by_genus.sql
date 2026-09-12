{{ config(materialized='table') }}

select genus, count(*) as tree_count
from {{ ref('stg_trees') }}
where genus is not null
group by 1
order by 2 desc
