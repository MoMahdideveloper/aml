# Track A Observability Contract

**Scope:** Platinum Heritage Flask CRM only (`app.py`, `views/`, `services/`, jobs).  
**Not in scope:** Track B (`api/`, `matcher/`, `ingestor/`, `chatbot/`).

## Operational questions → signals

| Question | Primary signals |
|----------|-----------------|
| Are users receiving errors? | `http_requests_total{status_class="5xx"}`, structured `http_request` events with `status_class` |
| Which routes/jobs are slow? | `http_request_duration_seconds` histogram by route/method; job duration events/metrics |
| Why did rec/notify/match/LLM fail? | `provider_call` events; `external_provider_*` metrics; job_failed with `failure_category` |
| Is DB/Redis/queue/provider unhealthy? | `/readyz` components; dependency metrics; readiness fail ≠ liveness fail |
| Can one request be reconstructed end-to-end? | `X-Request-ID` / `request_id` on logs, response, job metadata |

## Non-goals / rejected telemetry

- Full request/response bodies, prompts, customer record dumps  
- Metric labels for user_id, email, raw URL, request_id, error message text  
- Vendor-only formats that block local inspection  
- Enabling external alert channels without human approval  

## Field dictionary (structured logs)

| Field | Notes |
|-------|--------|
| `event` | Stable snake_case name |
| `request_id` | Correlation UUID (not a metric label) |
| `route` | Flask route template, e.g. `/customers/<int:customer_id>` |
| `method` | HTTP method |
| `status_class` | `2xx` / `3xx` / `4xx` / `5xx` |
| `duration_ms` | Integer milliseconds |
| `component` | `http`, `job`, `provider`, `db`, `health` |
| `error_category` | Bounded enum: `timeout`, `dependency`, `validation`, `auth`, `internal`, `unknown` |

## Metric label rules

Allow only: normalized `route` (template), `method`, `status_class`, `provider` (allowlist), `operation` (allowlist), `job_type` (allowlist), `outcome` (`ok`/`error`/`timeout`).

## Health semantics

| Endpoint | Meaning |
|----------|---------|
| `GET /healthz` | Process liveness only |
| `GET /readyz` | Required deps (DB; Redis when configured) with short timeouts |
| `GET /metrics` | Prometheus text exposition (optional scrape) |
