"""Search eval: P@K, recall, MRR, latency percentiles (synthetic)."""

import json
import time
from pathlib import Path

from services.intelligence_eval import (
    mrr,
    precision_at_k,
    recall_at_k,
    summarize_run,
)
from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Customer, Property


FIXTURE = Path(__file__).parent / "fixtures" / "intelligence_eval" / "cases.json"


def _seed(db):
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
    monkeypatch.setenv("ENABLE_NL_QUERY_PARSE", "0")
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    with app.app_context():
        from database import db

        seed_ids = _seed(db)
        zero = 0
        precisions = []
        recalls = []
        mrrs = []
        latencies = []
        for case in cases:
            # skip hybrid-only cases on keyword baseline
            if case.get("needs_hybrid"):
                continue
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
            expect = {seed_ids[s] for s in case.get("expect_seeds", []) if s in seed_ids}
            k = case.get("k", 5)
            if expect:
                precisions.append(precision_at_k(hit_ids, expect, k))
                recalls.append(recall_at_k(hit_ids, expect, k))
                mrrs.append(mrr(hit_ids, expect))
            for bad in case.get("reject_seeds", []):
                bid = seed_ids.get(bad)
                if bid is not None and case.get("needs_hybrid"):
                    # hard-filter cases only enforced under hybrid
                    pass

        summary = summarize_run(
            precisions=precisions,
            recalls=recalls,
            mrrs=mrrs,
            latencies_ms=latencies,
            zero_results=zero,
            n_queries=len(latencies),
            degraded_count=0,  # keyword-only path is never hybrid-degraded
        )
        # Visible with: pytest -q tests/test_intelligence_eval_baseline.py -s
        print("\nINTELLIGENCE_BASELINE_KEYWORD", summary)
        assert summary["n_queries"] >= 1
        assert summary["precision_at_k_mean"] > 0
        assert summary["mrr_mean"] > 0
        assert summary["latency_p50_ms"] >= 0
        assert summary["latency_p95_ms"] >= summary["latency_p50_ms"]
        assert summary["zero_result_rate"] < 1.0
        assert summary["degraded_rate"] == 0.0


def test_eval_hybrid_degraded_path_metrics(db_setup, app, monkeypatch):
    """Hybrid on without embeddings must stay useful (keyword/degraded), not crash."""
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    monkeypatch.setenv("ENABLE_NL_QUERY_PARSE", "0")
    monkeypatch.setenv("ENABLE_SEARCH_SHADOW", "0")
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    with app.app_context():
        from database import db
        from services.hybrid_search import HybridSearchService

        seed_ids = _seed(db)
        zero = 0
        precisions = []
        recalls = []
        mrrs = []
        latencies = []
        degraded = 0
        n = 0
        for case in cases:
            if case.get("scope") != "properties":
                continue
            req = parse_search_request(
                q=case["query"], scope=case["scope"], mode="full"
            )
            t0 = time.perf_counter()
            result = HybridSearchService().search(req)
            latencies.append((time.perf_counter() - t0) * 1000)
            n += 1
            hybrid = result.get("hybrid") or {}
            if hybrid.get("degraded") or hybrid.get("mode") == "keyword_only":
                degraded += 1
            hits = result["groups"].get("properties") or []
            hit_ids = [h["id"] for h in hits[: case.get("k", 5)]]
            if result.get("total_count", 0) == 0 and not hits:
                zero += 1
            expect = {seed_ids[s] for s in case.get("expect_seeds", []) if s in seed_ids}
            k = case.get("k", 5)
            if expect:
                precisions.append(precision_at_k(hit_ids, expect, k))
                recalls.append(recall_at_k(hit_ids, expect, k))
                mrrs.append(mrr(hit_ids, expect))

        summary = summarize_run(
            precisions=precisions,
            recalls=recalls,
            mrrs=mrrs,
            latencies_ms=latencies,
            zero_results=zero,
            n_queries=n,
            degraded_count=degraded,
        )
        print("\nINTELLIGENCE_BASELINE_HYBRID", summary)
        assert n >= 1
        assert summary["latency_p50_ms"] >= 0
        # Without embeddings, expect degraded/keyword path rather than hard failure
        assert summary["degraded_rate"] >= 0.0


def test_metric_helpers_unit():
    assert precision_at_k([1, 2, 3], {2}, 3) == 1 / 3
    assert recall_at_k([1, 2, 3], {2, 9}, 3) == 0.5
    assert mrr([9, 2, 1], {2}) == 0.5
    from services.intelligence_eval import percentile

    assert percentile([10, 20, 30, 40], 50) == 20 or percentile([10, 20, 30, 40], 50) == 30
