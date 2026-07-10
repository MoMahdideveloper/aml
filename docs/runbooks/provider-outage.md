# Runbook: External provider outage (LLM / geocode / SMS)

## Detection

- `external_provider_calls_total{outcome="timeout|error"}` spike  
- Logs: `event=provider_call` without prompt text

## Triage

1. Identify `provider` label (gemini, kie, nominatim, melipayamak).  
2. Check recent code deploy vs provider status page.  
3. Confirm timeouts in env (`GEMINI_REQUEST_TIMEOUT_SECONDS`, `KIE_TIMEOUT_SECONDS`).

## Mitigation

- Switch `LLM_PROVIDER` if dual-provider configured.  
- Disable AI autofill UI paths temporarily.  
- Geocode: set `GEOCODE_PROVIDER=off` for approx pins only.

## Recovery verification

- Provider outcome=ok ratio recovered; extract endpoint returns structured JSON (faked in tests).
