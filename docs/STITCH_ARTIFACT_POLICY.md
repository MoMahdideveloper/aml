# Stitch export versioning policy

Stitch exports under `stitch_kpi_performance_dashboard/` are **design references only**.
They are not loaded by Flask routes and are excluded from production Docker images.

## Track in Git (canonical)

Per screen folder, prefer:

| File | Purpose |
|------|---------|
| `code.html` | Canonical HTML export |
| `screen.png` | Visual reference |
| Curated docs | e.g. `platinum_heritage/TASTE_DESIGN.md`, root `.stitch/DESIGN.md` |

## Do not track (generated / noisy)

Ignored via `.gitignore` when untracked:

- `**/index.html` re-exports
- `**/screen_meta.json`
- `**/code1.html` duplicates
- Local `__pycache__` under the Stitch tree

## Sync scripts

- Keep paths **repository-relative** (no absolute developer home paths).
- Never commit sync output blindly; review `git status` under the Stitch tree first.

## Runtime independence

- Live UI lives only in `templates/` + `static/`.
- `tests/test_template_references.py` fails if code `render_template()`s a Stitch path.
- Production `.dockerignore` excludes the entire Stitch tree.
