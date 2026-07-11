# CRM intelligence — staging enablement checklist

Use this after deploy + `flask db upgrade` (head includes `x9y0z1a2b3c4` or later).

## 0. Preflight

- [ ] App boots: `python main.py`
- [ ] Migrations current: `flask db current` shows latest head
- [ ] Core smoke: `pytest -q tests/test_app_smoke.py tests/test_intelligence_eval_baseline.py`
- [ ] Admin can open `/admin/intelligence` and `/admin/vocab`

## 1. Safe defaults (leave unless needed)

| Toggle | Staging day 1 |
|--------|----------------|
| Global CRM search | **ON** |
| Hybrid shadow ranking | ON when testing hybrid |
| All others | **OFF** until steps below |

## 2. Vocabulary

- [ ] Create 3–5 terms in `/admin/vocab` (e.g. villa↔house, apt↔apartment)
- [ ] Enable **Vocabulary synonym expand**
- [ ] Search `/search?q=house&scope=properties` against a listing titled with villa/house
- [ ] Confirm expand does not log raw queries (check structured logs only)

## 2b. Customer NL (optional)

- [ ] Enable **Customer NL structured filters** on `/admin/intelligence`
- [ ] Search customers: `2 bedroom apartment under 500k` (or `two-bedroom …`)
- [ ] Confirm structured chips/meta; free-text preferences never searched
- [ ] Leave OFF if not needed

## 3. Hybrid (shadow first)

- [ ] On `/admin/intelligence`, note **Property embedding coverage** (missing count)
- [ ] Backfill missing embeddings asynchronously (`crm.sync_property_embedding`) if coverage is low
- [ ] Enable **Hybrid / natural-language search** + **Hybrid shadow ranking**
- [ ] Search `3 bedroom apartment under 500k` on properties
- [ ] UI order stays keyword-like; chips may show shadow
- [ ] API/meta includes `hybrid_top_ids` vs `keyword_top_ids`
- [ ] Turn **shadow OFF** only after comparison looks good

## 4. Occurrences / graph / context

- [ ] Enable **Vocabulary occurrences** → run Celery reindex or create/update a property
- [ ] Enable **Related entities graph** → Customer 360 **Related** + property related panel
- [ ] Enable **AI context** → open Customer 360 “AI context (JSON)”
- [ ] Enable **Grounded AI answers** → `POST /api/context/customer/<id>/answer`
- [ ] Keep **LLM query parse** OFF unless Gemini/Kie is configured and soft fill is desired

## 5. Description search (optional)

- [ ] Only if product accepts noise: enable **Search property descriptions**
- [ ] Otherwise leave OFF (recommended)

## 6. Rollback

- [ ] Any issue: open `/admin/intelligence` and turn features OFF
- [ ] Emergency: set `INTELLIGENCE_SETTINGS_USE_ENV=1` and env flags to 0, restart

## 7. Exit criteria for “staging ready”

- [ ] Keyword search works with all intelligence OFF
- [ ] At least one synonym expand success case
- [ ] Hybrid shadow compared once
- [ ] Context JSON loads for one customer and one property without note bodies
- [ ] No PII in application logs for search queries
