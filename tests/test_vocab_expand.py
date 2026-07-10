"""Query expand unit tests (no DB)."""

from services.vocab.expand import MAX_EXPANDED_KEYS, expand_query_terms


def test_synonym_bidirectional():
    groups = {
        "villa": ["house", "villa"],
        "house": ["house", "villa"],
    }
    keys = expand_query_terms("house", synonym_groups=groups)
    assert "villa" in keys
    assert "house" in keys


def test_replacement_before_synonym():
    replacements = {"sqm": "square meters"}
    groups = {
        "square meters": ["square meters", "sq meters"],
        "sq meters": ["square meters", "sq meters"],
    }
    keys = expand_query_terms("sqm", replacements=replacements, synonym_groups=groups)
    assert "square meters" in keys or any("square" in k for k in keys)
    assert "sqm" in keys or "square meters" in keys


def test_cap_at_eight():
    groups = {"a": [f"s{i}" for i in range(20)] + ["a"]}
    for i in range(20):
        groups[f"s{i}"] = groups["a"]
    keys = expand_query_terms("a", synonym_groups=groups, max_keys=MAX_EXPANDED_KEYS)
    assert len(keys) <= MAX_EXPANDED_KEYS


def test_empty_query():
    assert expand_query_terms("") == []
    assert expand_query_terms("   ") == []


def test_archived_not_in_maps():
    # expand only sees maps passed in; empty maps → original token only
    keys = expand_query_terms("Villa")
    assert "villa" in keys
    assert len(keys) >= 1
