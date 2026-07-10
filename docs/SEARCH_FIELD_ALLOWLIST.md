# Searchable field allowlist

Forbidden everywhere: passwords, secrets, `preferences` free text (may hold PII notes), deal `notes`, agent `bio` full text (too large/noise), embeddings, env vars.

## customers
| Field | Role |
|-------|------|
| id | exact identifier |
| name | primary display; prefix + contains |
| email | exact + prefix |
| phone | exact (digits) + contains digits |
| status | filter |
| customer_type | filter |
| location_preference | contains (secondary) |

## properties
| Field | Role |
|-------|------|
| id | exact identifier |
| file_code | exact identifier |
| title | primary; prefix + contains |
| address | secondary; prefix + contains |
| neighborhood | contains |
| status | filter |
| property_type | filter |
| listing_type | filter |

## deals
| Field | Role |
|-------|------|
| id | exact identifier |
| status | filter + secondary display |
| property_id / customer_id | exact via joined display only |
| offer_amount | display only (not free-text search) |

Search text matches related property title/file_code or customer name/email (allowlisted joins).

## agents
| Field | Role |
|-------|------|
| id | exact |
| name | primary; prefix + contains |
| email | exact + prefix |
| phone | exact digits |
| specialization | contains |
| is_deleted | exclude true |

## tasks
| Field | Role |
|-------|------|
| id | exact |
| title | primary; prefix + contains |
| status | filter |
| priority | filter |
| agent_id | filter |
