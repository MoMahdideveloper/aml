"""Search request validation."""

import pytest
from services.unified_search import SearchValidationError, parse_search_request


def test_min_length():
    with pytest.raises(SearchValidationError) as e:
        parse_search_request(q="a")
    assert e.value.code == "too_short"


def test_numeric_id_allowed_short():
    req = parse_search_request(q="7")
    assert req.normalized_query == "7"


def test_max_length():
    with pytest.raises(SearchValidationError) as e:
        parse_search_request(q="x" * 101)
    assert e.value.code == "too_long"


def test_bad_scope():
    with pytest.raises(SearchValidationError) as e:
        parse_search_request(q="ada", scope="customers,spaceships")
    assert e.value.code == "bad_scope"


def test_bad_sort():
    with pytest.raises(SearchValidationError) as e:
        parse_search_request(q="ada", sort="magic")
    assert e.value.code == "bad_sort"


def test_normalize_whitespace():
    req = parse_search_request(q="  Ada   Lovelace  ")
    assert req.normalized_query == "Ada Lovelace"


def test_autocomplete_limit_capped():
    req = parse_search_request(q="ada", mode="autocomplete", per_page="50")
    assert req.per_page <= 5
