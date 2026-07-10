# Import field dictionary

## Customer

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| name | yes | string ≤255 | |
| email | yes | email unique | lowercased |
| phone | yes | string ≤20 | digits normalized for match |
| budget_min | no | int ≥0 | default 0 |
| budget_max | no | int ≥0 | default 0 |
| preferred_bedrooms | no | int ≥0 | |
| preferred_bathrooms | no | int ≥0 | |
| preferred_type | no | string ≤50 | |
| location_preference | no | string ≤255 | |
| status | no | enum | active/prospect/lead/inactive |
| customer_type | no | enum | buyer/seller/both/investor |
| preferences | no | text ≤4000 | |
| external_id | no | string ≤64 | import-only exact key if provided in CSV (stored in row result only) |

**Exact duplicate:** normalized email OR normalized phone  
**Possible duplicate:** name similarity (bounded) without auto-merge  

## Property

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| title | yes | string ≤255 | |
| address | yes | text | normalized for match |
| property_type | yes | string ≤50 | |
| price | no | int ≥0 | maps to `price` |
| bedrooms | no | int | |
| bathrooms | no | int | |
| square_feet | no | int | |
| description | no | text | |
| status | no | string | default active |
| agent_id | no | int FK | |
| agent_email | no | string | resolves agent if agent_id empty |
| listing_type | no | sale/rental | |
| neighborhood | no | string | |
| file_code | no | string unique | listing identifier |
| year_built | no | int | |

**Exact duplicate:** file_code OR normalized address  
**Possible:** title + address similarity  

## Deal

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| property_id | yes* | int | *or property_file_code |
| customer_id | yes* | int | *or customer_email |
| agent_id | no | int | or agent_email |
| status | no | string | default prospecting |
| offer_amount | no | int ≥0 | |
| notes | no | text | |
| external_id | no | string | exact deal key |

**Exact duplicate:** external_id OR (property_id + customer_id + status)  

## Unsupported
Excel, Sheets, CRM connectors, task/agent bulk import (agents referenced only).
