{{ config(materialized='table') }}

with daily as (
    select * from {{ ref('stg_weather') }}
),
cutoff as (
    select max(obs_date) - interval 2 year as start_date from daily
)

select obs_date, tmax_f, tmin_f, precip_in
from daily, cutoff
where obs_date >= cutoff.start_date
order by obs_date
