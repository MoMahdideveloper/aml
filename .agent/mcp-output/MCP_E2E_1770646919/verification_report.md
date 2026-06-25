# Playwright MCP Verification Report (Targeted Re-test)

Run ID: `MCP_E2E_1770646919`  
Base URL: `http://127.0.0.1:5000`

## What Was Re-tested

1. Recommendations detail schedule viewing flow
- Page: `/recommendations/1`
- Action: Click **Schedule Viewing**, load scheduler, submit form.
- Expected: Requests hit `/properties/<id>/schedule-viewing` and succeed (no 405), modal closes.
- Result: PASS
- Evidence:
  - Network log: `.agent/mcp-output/MCP_E2E_1770646919/reco_schedule_viewing_network.json`
    - `GET /properties/1/schedule-viewing?... => 200`
    - `POST /properties/1/schedule-viewing => 200`

2. Property detail AI extraction render
- Page: `/properties/1/detail`
- Action: Paste listing text, click **Scan with AI**, ensure extracted fields render (not blank).
- Expected: `POST /api/ai/parse/property => 200`, UI displays extracted fields + Apply buttons (or deterministic error state).
- Result: PASS
- Evidence:
  - Network log: `.agent/mcp-output/MCP_E2E_1770646919/property_ai_extract_network.json`
    - `POST /api/ai/parse/property => 200`

## Console / Runtime Notes
- Console warnings: `.agent/mcp-output/MCP_E2E_1770646919/console_warnings.log`
- No console errors observed during these two flows.

