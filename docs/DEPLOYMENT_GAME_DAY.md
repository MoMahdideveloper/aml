# Deployment game day (staging only)

**Do not run against production.**

## Drill steps

1. Deploy known-good image to staging (`dry_run=false` when configured).  
2. Record baseline: `/readyz`, `/metrics` 5xx, sample latency.  
3. Deploy intentionally failing candidate (bad config or failing readiness).  
4. Detect failure via readiness or post_deploy_verify.  
5. Roll back to known-good via **Application rollback** workflow.  
6. Verify service + synthetic data integrity.  
7. Record timings (detect, decide, restore) vs RTO target.  

## Record template

| Metric | Value |
|--------|-------|
| Detect time | |
| Rollback start | |
| Service restored | |
| Data loss vs RPO | none / describe |
| Gaps found | |
| Runbook updates | |

## Acceptance

- Rollback meets proposed RTO for staging  
- No synthetic data loss beyond approved RPO  
- Runbook updated from results  
