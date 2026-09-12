{{ config(materialized='table') }}

select
    geoid,
    name,
    population,
    median_age,
    median_hh_income,
    median_home_value,
    households,
    occupied_housing,
    owner_occupied,
    renter_occupied,
    round(100.0 * renter_occupied / nullif(occupied_housing, 0), 1) as renter_pct,
    round(100.0 * owner_occupied / nullif(occupied_housing, 0), 1)  as owner_pct,
    edu_pop_25plus,
    bachelors,
    masters,
    professional,
    doctorate,
    bachelors + masters + professional + doctorate                  as bachelors_plus,
    round(
        100.0 * (bachelors + masters + professional + doctorate)
        / nullif(edu_pop_25plus, 0),
        1
    ) as bachelors_plus_pct
from {{ ref('stg_demographics') }}
