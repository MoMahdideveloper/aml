# Secure CRM document policy (first release)

## Categories
`identity`, `mandate`, `contract`, `disclosure`, `property_document`, `offer`, `correspondence`, `other`

## Formats (fail closed)
| Type | Magic | Max decode |
|------|-------|------------|
| PDF | `%PDF` | basic structure, max 25MB |
| JPEG | FF D8 FF | max 40MP pixels |
| PNG | 89 PNG | max 40MP pixels |
| WebP | RIFF….WEBP | max 40MP |
| plain text | UTF-8 text only | max 2MB |

**Rejected:** SVG, HTML, XML, executables, Office macros, zip, polyglots.

## Limits
- Max file size: **10 MB** (default)
- Max documents per owner (available + pending): **50**
- Display name max: **200** chars
- Original filename stored sanitized, max **255** (metadata only; never used as path)

## Visibility
Authenticated CRM staff (`agent`/`admin`) with global staff model (same as deals list).
Anonymous denied. Viewer role: list metadata only if product later adds; v1 same as agent read for list, write requires agent/admin.

## Versioning
- Logical document group ID (`document_group_id`)
- Monotonic `version` per group
- New version: previous versions immutable; latest marked `is_latest`
- Duplicate checksum within same owner: warn; allow separate group or cancel

## Status lifecycle
`pending_scan` → `available` | `quarantined` | `failed`  
`available` → `archived`  
Download only when `available`.  
Archive ≠ hard delete (storage retained).

## Scanner
Development: deterministic fake scanner (passes known-good fixtures, rejects EICAR-like bytes).  
Production: require `DOCUMENT_SCANNER=clamav|external` or explicit `DOCUMENT_ALLOW_UNSCANNED=0` fail-closed (default: development allow after fake pass).

## Download
- Authz required every time
- `Content-Disposition: attachment` with sanitized name
- `X-Content-Type-Options: nosniff`
- `Cache-Control: private, no-store`
- Inline preview only for PDF/JPEG/PNG/WebP when `?inline=1` and type safe

## Storage root
- Dev/test: `instance/document_store/` or temp dir from env `DOCUMENT_STORAGE_ROOT`
- Production: must set `DOCUMENT_STORAGE_ROOT` outside web root (documented)
