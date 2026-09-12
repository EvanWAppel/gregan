-- LA County Environmental Health restaurant & market inspections, filtered to
-- Glendora at load (see build_warehouse.filter_table_to_city). ONE ROW PER
-- INSPECTION ACTIVITY — a facility appears once per program/visit. Non-spatial
-- (address/zip only). The raw load is all text; cast the typed columns here.

with source as (
    select * from {{ source('raw', 'restaurant_inspections') }}
)

select
    "SERIAL NUMBER"                                        as serial_number,
    "FACILITY ID"                                         as facility_id,
    "FACILITY NAME"                                       as facility_name,
    "OWNER NAME"                                          as owner_name,
    try_strptime(trim("ACTIVITY DATE"), '%m/%d/%Y')::date as activity_date,
    "PROGRAM NAME"                                        as program_name,
    "PROGRAM STATUS"                                      as program_status,
    "PE DESCRIPTION"                                      as pe_description,
    "FACILITY ADDRESS"                                    as facility_address,
    "FACILITY CITY"                                       as facility_city,
    "FACILITY ZIP"                                        as facility_zip,
    "SERVICE DESCRIPTION"                                 as service_description,
    try_cast("SCORE" as integer)                          as score,
    "GRADE"                                               as grade
from source
