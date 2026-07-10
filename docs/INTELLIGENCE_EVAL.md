# Intelligence evaluation baseline (Phase 0)

Synthetic fixtures only. Never use production customer text.

## Fixture location
`tests/fixtures/intelligence_eval/cases.json`

## Metrics
| Metric | Definition |
|--------|------------|
| precision@k | fraction of top-k hits in expected id set |
| zero_result_rate | queries with total_count == 0 |
| latency_ms | wall time for `unified_search` / hybrid path |

## Baseline command
```bash
pytest -q tests/test_intelligence_eval_baseline.py -s
```

## Targets (post residual R0)
- Flag-off path: zero regression vs baseline zero_result_rate on fixture ids
- Hybrid+constraints on: hard-filter cases must exclude known false positives
- Provider-down: same as keyword path (degraded)
- Shadow mode: display order matches keyword_top_ids while hybrid_top_ids may differ

## Residual flags (admin `/admin/intelligence`)
- `search_shadow` — hybrid compute, keyword display
- `description_search` — optional description keyword (default off)

Record numbers from local runs in PR notes; do not commit production metrics.

