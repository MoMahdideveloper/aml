# Database rollback policy (Track A)

## Principles

1. **Prefer forward corrective migrations** that fix schema/data in place.  
2. **Application rollback** to a prior image is allowed only when the DB schema remains compatible with that image.  
3. **Alembic downgrade** only when explicitly proven data-safe and approved.  
4. **Destructive DB rollback** requires verified backup + separate human approval (see DR contract).

## Compatibility window

Document for each release:

- Minimum app version that works with current schema  
- Whether prior app image can run against new schema (expand/contract pattern preferred)

## Before app rollback

```text
[ ] Confirm target image SHA
[ ] Confirm schema compatible (confirm_schema_compatible=true)
[ ] Backup/checkpoint available
[ ] Communication plan
```

## Forbidden without approval

- `drop_table` / mass DELETE as emergency cleanup  
- Restoring production backup over live DB without DR runbook  
- Automatic downgrade in entrypoint  
