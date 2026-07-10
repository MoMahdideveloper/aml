# Unified search — operator & developer guide

## Users
- Shell search (desktop strip + mobile button) when logged in and `ENABLE_GLOBAL_SEARCH=1`.
- Type ≥2 characters for autocomplete; `/` focuses search (when not in another field).
- Full results: `/search?q=…`
- Customer saved views: filter Clients → **Save view** → chips to reapply → Manage.

## Ranking (deterministic)
1. Exact record ID  
2. Exact email / file_code  
3. Prefix match  
4. Contains match  
Ties: lower id first. No fuzzy scoring.

## Fields
See `docs/SEARCH_FIELD_ALLOWLIST.md`. Notes/bio/preferences not searchable.

## Limits
Autocomplete 5/group; full page 20/group. Query max 100 chars.

## Saved views
- Store versioned JSON filters only (`v`, allowlisted keys). Never SQL.
- Private to owner; apply/delete/default CSRF-protected POST.
- Customer vertical slice first; extend scopes carefully.

## Flags
`ENABLE_GLOBAL_SEARCH=0` hides UI and returns 404 on search routes.

## Telemetry
`search_completed` events: duration, counts, zero_results — **not** query text.

## Extension
1. Add fields to allowlist doc.  
2. Extend repository method.  
3. Tests for ranking + permissions.  
4. Optional index only after EXPLAIN on realistic data.
