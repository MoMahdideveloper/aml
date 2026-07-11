"""Privacy-safe search evaluation metrics (synthetic fixtures only)."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set


def precision_at_k(hit_ids: Sequence[int], relevant: Set[int], k: int) -> float:
    if k <= 0 or not relevant:
        return 0.0
    top = list(hit_ids)[:k]
    if not top:
        return 0.0
    return len(set(top) & relevant) / float(min(k, len(top)))


def recall_at_k(hit_ids: Sequence[int], relevant: Set[int], k: int) -> float:
    if not relevant:
        return 1.0 if not hit_ids else 0.0
    top = set(list(hit_ids)[:k])
    return len(top & relevant) / float(len(relevant))


def mrr(hit_ids: Sequence[int], relevant: Set[int]) -> float:
    """Mean reciprocal rank for a single query (0 if no relevant in list)."""
    if not relevant:
        return 0.0
    for i, hid in enumerate(hit_ids, start=1):
        if hid in relevant:
            return 1.0 / float(i)
    return 0.0


def percentile(values: Sequence[float], p: float) -> float:
    """Nearest-rank percentile; p in [0, 100]."""
    if not values:
        return 0.0
    xs = sorted(float(v) for v in values)
    if len(xs) == 1:
        return xs[0]
    p = max(0.0, min(100.0, float(p)))
    idx = int(round((p / 100.0) * (len(xs) - 1)))
    return xs[idx]


def summarize_run(
    *,
    precisions: Sequence[float],
    recalls: Sequence[float],
    mrrs: Sequence[float],
    latencies_ms: Sequence[float],
    zero_results: int,
    n_queries: int,
    degraded_count: int = 0,
) -> Dict[str, float]:
    n = max(1, int(n_queries))
    return {
        "n_queries": float(n_queries),
        "precision_at_k_mean": sum(precisions) / max(1, len(precisions)) if precisions else 0.0,
        "recall_at_k_mean": sum(recalls) / max(1, len(recalls)) if recalls else 0.0,
        "mrr_mean": sum(mrrs) / max(1, len(mrrs)) if mrrs else 0.0,
        "zero_result_rate": float(zero_results) / float(n),
        "degraded_rate": float(degraded_count) / float(n),
        "latency_p50_ms": percentile(latencies_ms, 50),
        "latency_p95_ms": percentile(latencies_ms, 95),
        "latency_mean_ms": sum(latencies_ms) / max(1, len(latencies_ms)) if latencies_ms else 0.0,
    }
