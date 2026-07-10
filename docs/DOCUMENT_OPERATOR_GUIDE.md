# Secure document management — operator guide

## Architecture
- Metadata in `documents` / `document_audit_logs`
- Bytes in private root (`DOCUMENT_STORAGE_ROOT` or `instance/document_store/`)
- Never under `static/`
- Downloads only via `/documents/<id>/download` after authz

## Storage layout
```
{DOCUMENT_STORAGE_ROOT}/
  available/
  quarantine/
  archived/
  tmp/
```

## Production
Set `DOCUMENT_STORAGE_ROOT` to a path **outside** the web root.  
Missing config fails when `FLASK_ENV=production`.

## Deal vertical slice
1. Open deals list  
2. `/deals/<id>/documents`  
3. Upload PDF  
4. Download when status `available`  
5. New version / Archive  

Also: `/customers/<id>/documents`, `/properties/<id>/documents`, `/agents/<id>/documents`

## Scanner
Dev: `fake_scanner` (rejects EICAR marker).  
Does not claim real AV. Production scanner requires human approval.

## Consistency
```bash
python scripts/document_consistency.py
```
Read-only; repair not auto-enabled.

## Backup
Include DB + entire `DOCUMENT_STORAGE_ROOT`. Restore DB first, then files; verify with consistency script.
