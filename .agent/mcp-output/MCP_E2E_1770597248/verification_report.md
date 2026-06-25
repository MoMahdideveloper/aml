# Playwright MCP Verification Report (MCP_E2E_1770597248)

- Date: 2026-02-09
- Base URL: http://127.0.0.1:5000
- Test DB (isolated): instance/playwright_mcp_MCP_E2E_1770597248.db (delete during cleanup to undo all changes)
- Server PID: recorded in $outDir/server.pid

## Summary

- Pages verified: 15
- Result: **2 failures**, **1 partial** (admin rollback), remainder pass

### High Severity Defects

1. **DEF-REC-001 (blocker): Recommendations "Schedule Viewing" submits to wrong URL (405)**
   - Page: /recommendations/1
   - Action: Schedule Viewing (from recommendation card)
   - Expected: POST should create viewing (or show success) without leaving recommendations page.
   - Actual: POST to /recommendations/1 returns **405 Method Not Allowed**.
   - Evidence:
     - Network: $outDir/08_recommendations_detail_network.json
     - Console: $outDir/08_recommendations_detail_console.json
     - Screenshot: $outDir/def_reco_schedule_viewing_405.png
   - Repro:
     1. Open /recommendations/1
     2. Click **Schedule Viewing** on a recommendation
     3. Fill required fields (Customer, Agent, Date, Time)
     4. Click **Schedule Viewing**

2. **DEF-AI-001 (high): Property detail AI extraction returns 200 but UI renders nothing**
   - Page: /properties/4/detail
   - Action: AI Data Extraction -> Scan with AI
   - Expected: Extracted fields appear + Apply-to-form works (or at least a user-visible fallback error).
   - Actual: Request returns **200 OK** but #ai-results and #ai-error remain hidden/empty; no Apply UI.
   - Evidence:
     - Network: $outDir/14_property_detail_network.json (POST /api/ai/parse/property => 200)
     - Screenshot: $outDir/def_property_ai_no_results.png
     - Note: Manual fetch inspection showed response shape { confidence, data, entity, missing }, suggesting a frontend/back-end contract mismatch.
   - Repro:
     1. Open /properties/4/detail
     2. Paste any listing text into AI panel
     3. Click **Scan with AI**
     4. Observe: no extracted fields shown

### Medium / Observations

- **OBS-ADMIN-001 (medium): Admin Environment Rollback unclear**
  - POST /admin/environment/rollback returned **200 OK**, but value did not visibly revert (needs deeper verification).
  - Evidence: $outDir/13_admin_environment_network.json, $outDir/tmp_admin_env_after_rollback_snapshot.md

- **OBS-DL-001 (low): Export PDF downloads intercepted by IDM integration**
  - Export attempted, but requests show 204 Intercepted by the IDM Advanced Integration in $outDir/08b_recommendations_detail_network_after_pdf.json.
  - API-side export works (JSON via XHR returned 200 with keys properties, etc.).

- Tailwind CDN warning appears on most pages (console warnings), no runtime JS errors except those listed above.

## Page-by-Page Results

| # | Route | Status | Key Checks | Artifacts |
|---:|---|---|---|---|
| 1 | / | PASS | KPIs + recent lists render; CTAs navigate to properties/tasks/deals | $outDir/01_overview_console.json, $outDir/01_overview_network.json |
| 2 | /properties | PASS | Filters + add property + detail update (incl square_feet=0) | $outDir/02_properties_console.json, $outDir/02_properties_network.json |
| 3 | /agents | PASS | Add/edit/delete agent (CSRF ok) | $outDir/03_agents_console.json, $outDir/03_agents_network.json |
| 4 | /customers | PASS | Add/edit/delete customer; details panel loads | $outDir/04_customers_console.json, $outDir/04_customers_network.json |
| 5 | /deals | PASS | Create/update/delete deal; modals load; export works | $outDir/05_deals_console.json, $outDir/05_deals_network.json |
| 6 | /tasks | PASS | Create/complete/delete task; calendar renders | $outDir/06_tasks_console.json, $outDir/06_tasks_network.json |
| 7 | /recommendations | PASS | Customer cards render; hooks present (.customer-selection-card, #createDealModal) | $outDir/07_recommendations_console.json, $outDir/07_recommendations_network.json |
| 8 | /recommendations/1 | FAIL | Create deal ok; **Schedule Viewing 405**; export endpoint OK | $outDir/08_recommendations_detail_*, $outDir/08b_recommendations_detail_* |
| 9 | /market-analysis | PASS | Generate analysis; Download JSON works | $outDir/09_market_analysis_* |
| 10 | /settings | PASS | Settings update + feedback; reverted after check | $outDir/10_settings_* |
| 11 | /admin/automations | PASS (read-only) | Page renders; no create/test UI present | $outDir/11_admin_automations_* |
| 12 | /admin/login | PASS | Invalid password feedback; valid login redirects to environment | $outDir/12_admin_login_* |
| 13 | /admin/environment | PARTIAL | CRUD ok; validation + health ok; rollback unclear | $outDir/13_admin_environment_* |
| 14 | /properties/4/detail | FAIL | Update ok; **AI extraction UI shows no results** | $outDir/14_property_detail_*, $outDir/def_property_ai_no_results.png |
| 15 | /properties/compare | PASS | Compare renders; remove updates URL; empty state ok | $outDir/15_compare_* |

## Cleanup Checklist (Undo All Changes)

1. Stop server: kill PID from $outDir/server.pid
2. Delete test DB file: instance/playwright_mcp_MCP_E2E_1770597248.db
3. (Optional) Remove .agent/mcp-output/MCP_E2E_1770597248/ after reviewing artifacts.
