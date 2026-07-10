"""Vocab normalizer pure unit tests."""

from services.vocab.normalize import normalize_display, normalize_key


def test_normalize_empty():
    assert normalize_key("") == ""
    assert normalize_key("   ") == ""
    assert normalize_display(None) == ""


def test_normalize_casefold_and_ws():
    assert normalize_key("  Villa  One  ") == "villa one"
    assert normalize_display("  Villa  One  ") == "Villa One"


def test_normalize_nfkc_and_edge_punct():
    # fullwidth digit ６ → 6 via NFKC
    assert normalize_key("\uff16villa") == "6villa"
    assert normalize_key('"villa"') == "villa"
    assert normalize_key("(apt)") == "apt"
