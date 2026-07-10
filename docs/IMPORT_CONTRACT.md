# CSV import contract (Track A)

## Format
- UTF-8 CSV (optional BOM)
- One entity type per file: `customer` | `property` | `deal`
- Header row required
- Max file size: **2 MB**
- Max rows: **500** (atomic full-batch transaction)
- Max columns: **40**
- Max field length: **4000** chars

## Modes
- **create_only** (default): never update existing rows; exact duplicates → skip
- Updates / merges: out of scope for v1 (require explicit future mode)

## Blank values
- Empty string / whitespace → treat as missing (use model default when optional)

## Dates / money / bool
- Dates: `YYYY-MM-DD`
- Money/integers: digits only (commas stripped)
- Booleans: `true`/`false`/`1`/`0`/`yes`/`no` (case-insensitive)

## Partial failure
- Preview: no business writes
- Execute: **full atomic batch** — any hard failure after start rolls back entire import
- Invalid rows counted at validation; user must fix file or map and re-upload (invalid rows block execute unless `skip_invalid=true` on execute — default **false**: all rows must be valid or exact-duplicate-skip)

## File handling
- Temp storage under `instance/imports/` (not permanent)
- File hash (SHA-256) for idempotency
- Cleanup after execute/failure (metadata retained)
