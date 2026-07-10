"""Hybrid merge pure unit tests."""

from services.hybrid_search import rrf_merge, weighted_merge


def test_rrf_prefers_consensus():
    kw = [1, 2, 3]
    sem = [3, 1, 4]
    merged = rrf_merge(kw, sem)
    ids = [pid for pid, _ in merged]
    # 1 and 3 appear in both → should rank ahead of unique-only mid ranks
    assert ids[0] in (1, 3)
    assert 4 in ids


def test_weighted_merge_uses_both_signals():
    kw = {10: 1.0, 11: 0.2}
    sem = {10: 0.1, 11: 1.0}
    merged = weighted_merge(kw, sem, kw_w=0.5, sem_w=0.5)
    # 11 wins on semantic, 10 on keyword — both present
    ids = [pid for pid, _ in merged]
    assert set(ids) == {10, 11}
