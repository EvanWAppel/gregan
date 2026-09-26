with source as (
    select * from {{ source('raw', 'air_quality') }}
),

deduped as (
    select
        site_num,
        local_site_name                          as site,
        county_name                              as county,
        try_cast(latitude as double)             as latitude,
        try_cast(longitude as double)            as longitude,
        try_cast(date_local as date)             as obs_date,
        parameter_name                           as pollutant,
        max(units)                               as units,
        avg(try_cast(arithmetic_mean as double)) as concentration,
        avg(try_cast(aqi as double))             as aqi
    from source
    group by 1, 2, 3, 4, 5, 6, 7
)

select
    site_num,
    site,
    county,
    latitude,
    longitude,
    obs_date,
    pollutant,
    units,
    concentration,
    round(aqi) as aqi,
    case
        when aqi <= 50  then 'Good'
        when aqi <= 100 then 'Moderate'
        when aqi <= 150 then 'Unhealthy for Sensitive Groups'
        when aqi <= 200 then 'Unhealthy'
        when aqi <= 300 then 'Very Unhealthy'
        else 'Hazardous'
    end as aqi_category
from deduped
where obs_date is not null
  -- Scope each monitor to the pollutant it represents (see city_config AQS_SITE_*):
  -- in-city ozone from Glendora (site 0016); nearest live PM2.5 from Pasadena
  -- (site 2005). Pasadena also reports ozone, which we drop here so the "Ozone"
  -- series stays purely in-city rather than blending two monitors under one label.
  and (
    (site_num = '0016' and pollutant = 'Ozone')
    or (site_num = '2005' and pollutant like 'PM2.5%')
  )
