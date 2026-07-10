# Release runbook (Track A)

## Prerequisites

- [ ] PR CI green (css, lint, test matrix, postgres, redis, http-smoke)
- [ ] Staging artifact image tag known (`gptvli-web:<sha>` or registry)
- [ ] Migration preflight reviewed (`scripts/ci/migration_preflight.py`)
- [ ] On-call available for monitor window
- [ ] Backup/checkpoint taken if schema change (see DR docs)

## Staging promotion

1. Actions → **Deploy staging (manual)**  
2. Input `image_tag` = immutable SHA from **Release image** workflow  
3. Start with `dry_run=true` to validate wiring  
4. When Environment secrets configured: `dry_run=false`  
5. Confirm `/readyz` and post-deploy verify pass  

## Production approval

1. Actions → **Promote production (manual approval)**  
2. Same `image_tag` as staging (never rebuild from branch in prod job)  
3. GitHub Environment **production** requires reviewer  
4. `dry_run=true` until live adapter + secrets approved  

## Migration decision

| Situation | Action |
|-----------|--------|
| No schema change | Deploy app only; `RUN_MIGRATIONS=0` if ops-managed |
| Additive migration | Preflight + upgrade on staging first |
| Destructive SQL in script | Human approval + `--allow-destructive` + backup |
| Multiple alembic heads | **Block** until merged |

Prefer **forward corrective** migrations over downgrade.

## Verification

```bash
python scripts/ci/post_deploy_verify.py --base-url https://staging.example
curl -fsS "$BASE/healthz"
curl -fsS "$BASE/readyz"
curl -fsS "$BASE/metrics" | head
```

## Monitoring window

- 30–60 minutes: 5xx rate, p95 latency, readiness, job failures (see observability alerts)  
- Rollback if thresholds breached (ALERTS.md)

## Rollback triggers

- Sustained 5xx > 5% for 5m  
- `/readyz` failing  
- Critical migration/data issue  

## Rollback steps

1. Actions → **Application rollback**  
2. `target_image_tag` = last known-good  
3. `confirm_schema_compatible=true` only if schema allows  
4. Verify with post_deploy_verify  
5. DB rollback only per `docs/DATABASE_ROLLBACK_POLICY.md`  

## Escalation

- Eng on-call → product owner for customer impact  
- Preserve request IDs and deployment SHA in incident notes  

## Evidence retention

- GitHub Actions logs (default retention)  
- `release-metadata.json` artifact  
- Do not store customer dumps in CI artifacts  
