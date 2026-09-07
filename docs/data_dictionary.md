# Data Dictionary

This document defines the schema for the Neighbourhood Heat-Risk dataset used throughout the system. 

| Field | Description | Data Type | Range / Format | Source | Used In |
| ----- | ----------- | --------- | -------------- | ------ | ------- |
| `neighbourhood_id` | Unique identifier for a neighbourhood | String | E.g., NH-001 | Identity | Phase 10 (Override) |
| `neighbourhood_name` | Name of the neighbourhood | String | E.g., Chennai North Zone 1 | Identity | Phase 9 (Communication) |
| `district` | Name of the parent district | String | E.g., Chennai | Identity | Filtering |
| `latitude` | Geographical latitude | Float | -90.0 to 90.0 | Identity | Map UI |
| `longitude` | Geographical longitude | Float | -180.0 to 180.0 | Identity | Map UI |
| `observation_date` | Date of the environmental observation | Date | ISO Format | Temperature | Data Freshness |
| `temperature_c` | Ambient temperature in Celsius | Float | 0 to 60.0 | Temperature | Phase 4, 5, 9, 12 |
| `heat_index` | Felt temperature incorporating humidity | Float | > temperature_c | Temperature | Phase 5 |
| `humidity_percent` | Ambient humidity | Float | 0.0 to 100.0 | Temperature | Feature Engineering |
| `built_density` | Density of built environment | Float | 0.0 to 1.0 | Built Env | Phase 5 |
| `green_cover_percent` | Percentage of green cover | Float | 0.0 to 100.0 | Built Env | Phase 5 |
| `impervious_surface_percent` | Percentage of impervious surfaces | Float | 0.0 to 100.0 | Built Env | Phase 5 |
| `urban_heat_exposure_score` | Derived score representing heat exposure | Float | > 0.0 | Built Env | Phase 5 |
| `healthcare_distance_km` | Distance to nearest healthcare facility | Float | >= 0.0 | Service Access | Phase 5 |
| `healthcare_capacity` | Max daily capacity of nearest facility | Int | >= 0 | Service Access | Phase 7 |
| `transport_access_score` | Score representing public transport quality | Float | 0.0 to 1.0 | Service Access | Phase 5 |
| `estimated_people_reachable` | Estimated reachable people per day | Int | >= 0 | Service Access | Phase 7, 8 |
| `travel_time_minutes` | Est. travel time to neighbourhood | Float | >= 0.0 | Service Access | Phase 7 |
| `service_time_minutes` | Est. service time per team visit | Float | >= 0.0 | Service Access | Phase 7 |
| `vulnerability_index` | Aggregate index of vulnerability | Float | 0.0 to 1.0 | Vulnerability | Phase 5, 7 |
| `elderly_population_percent` | % of population over 65 | Float | 0.0 to 1.0 | Vulnerability | Phase 5 |
| `low_income_indicator` | Indicator of predominantly low income | Boolean | True/False | Vulnerability | Phase 5 |
| `total_population` | Total population in neighbourhood | Int | >= 0 | Population | Phase 7, 8 |
| `mobile_population` | Population unable to shelter | Int | >= 0, <= total_pop | Population | Phase 7, 8 |
| `mobile_population_percent` | Ratio of mobile to total population | Float | 0.0 to 1.0 | Population | Phase 7, 8 |
| `group_mobile` | Flag indicating high mobile pop. zone | Boolean | True/False | Fairness | Phase 8 |
| `group_low_service_access` | Flag indicating low service access zone | Boolean | True/False | Fairness | Phase 8 |
| `data_source` | Source of the dataset | String | E.g., synthetic | Metadata | Audit |
| `generated_at` | Timestamp of data generation/ingestion | Datetime | ISO Format | Metadata | Phase 6 |
| `dataset_version` | Version of the dataset | String | E.g., 1.0.0 | Metadata | Audit |
| `synthetic_data` | Flag if data is artificially generated | Boolean | True/False | Metadata | System Warning |
| `baseline_temperature_feature` | Configured temperature field used | String | E.g., latest_temperature_c | Baseline | Phase 12 |
| `baseline_temperature_value` | Raw temperature value for baseline | Float | NaN if missing | Baseline | Phase 12 |
| `baseline_score` | Baseline temperature score | Float | NaN if missing | Baseline | Phase 12 |
| `baseline_rank` | Integer priority rank | Int | 1 to N, None if missing | Baseline | Phase 12 |
| `baseline_priority` | Categorical priority assignment | String | HIGH/MEDIUM/LOW/DATA_INSUFFICIENT | Baseline | Phase 9, 12 |
| `baseline_selected` | Flag if chosen for priority outreach | Boolean | True/False | Baseline | Phase 7, 12 |
| `baseline_status` | Status of baseline record | String | RANKED/DATA_INSUFFICIENT | Baseline | Phase 6 |

