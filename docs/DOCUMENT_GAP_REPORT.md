# Document management — discovery gap report

## Existing upload/download surfaces

| Route/area | Path | Auth | Storage | Notes |
|------------|------|------|---------|-------|
| Property media gallery | `views/property_media.py` | CRM session (list auth) | `static/uploads/` | Extension-only allowlist; public URL under `/static/uploads/` |
| Property listing image | `views/property_listing.py` | API | static/uploads pattern | Marketing images |
| Import CSV | `views/imports.py` | agent/admin | `instance/imports/` temp | Temp only; cleaned after execute |
| Analysis export | `views/analysis.py` | varies | `send_file` | Generated reports, not user uploads |
| CSV report export | `views/reports.py` | agent/admin | in-memory Response | Not document store |

## PropertyImage model
- Filename + property_id only; no checksum, scan state, versioning, or private storage.
- **Reuse decision: DO NOT extend PropertyImage for CRM legal documents.** Keep gallery separate. New `Document` model + private storage root.

## Gaps vs secure document requirements
1. Files under `static/` are web-server-reachable.
2. Trusts extension / `secure_filename`, not magic bytes.
3. No quarantine/scan lifecycle.
4. No versioning, archive, or download audit.
5. No opaque storage keys.
6. No deal/customer/agent document panels.

## Decision
Implement parallel **Secure Document Management** subsystem; leave property media untouched.
