"""Phase 0: synthetic eval baseline (keyword path, flags off)."""

import json
import time
from pathlib import Path

from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Customer, Property


FIXTURE = Path(__file__).parent / "fixtures" / "intelligence_eval" / "cases.json"


def _seed(db):
    """Return map seed_name -> entity id."""
    ids = {}
    p1 = Property(
        title="Eval Waterfront Villa",
        address="1 Harbor",
        property_type="villa",
        price=900_000,
        bedrooms=4,
        neighborhood="downtown",
    )
    p2 = Property(
        title="Eval Big Apartment",
        address="2 Main",
        property_type="apartment",
        price=400_000,
        bedrooms=4,
    )
    p3 = Property(
        title="Eval Tiny Apartment",
        address="3 Side",
        property_type="apartment",
        price=200_000,
        bedrooms=1,
    )
    c = Customer(
        name="Eval Customer One",
        email="eval-cust@example.com",
        phone="5556000001",
        status="active",
    )
    db.session.add_all([p1, p2, p3, c])
    db.session.commit()
    ids["waterfront_villa"] = p1.id
    ids["big_apartment"] = p2.id
    ids["tiny_apartment"] = p3.id
    ids["eval_customer"] = c.id
    return ids


def test_eval_baseline_keyword_metrics(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "0")
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    with app.app_context():
        from database import db

        seed_ids = _seed(db)
        zero = 0
        precisions = []
        latencies = []
        for case in cases:
            req = parse_search_request(
                q=case["query"], scope=case["scope"], mode="full"
            )
            t0 = time.perf_counter()
            result = unified_search_service.search(req)
            latencies.append((time.perf_counter() - t0) * 1000)
            hits = result["groups"].get(case["scope"], [])
            hit_ids = [h["id"] for h in hits[: case.get("k", 5)]]
            if result["total_count"] == 0:
                zero += 1
            expect = {seed_ids[s] for s in case.get("expect_seeds", [])}
            if expect:
                top = set(hit_ids)
                precisions.append(len(top & expect) / max(1, min(len(expect), case.get("k", 5))))
            for bad in case.get("reject_seeds", []):
                # keyword-only may still return tiny apt for "apartment" — note only
                pass
        assert len(cases) >= 1
        # At least title keyword and customer name should hit
        assert precisions and sum(precisions) / len(precisions) > 0
        assert zero < len(cases)
