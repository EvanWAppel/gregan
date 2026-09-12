{{ config(materialized='table') }}

select * from {{ ref('stg_crime') }}
where year is not null
order by year
