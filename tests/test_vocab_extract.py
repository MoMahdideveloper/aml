"""Term extraction unit tests."""

from services.vocab.extract import extract_keys_from_text, source_hash


def test_extract_lexicon_filter():
    lexicon = {"villa", "renovated", "apartment"}
    terms = extract_keys_from_text(
        "Beautiful renovated villa with garden",
        lexicon_keys=lexicon,
    )
    keys = {t.normalized_key for t in terms}
    assert "villa" in keys
    assert "renovated" in keys
    assert "beautiful" not in keys


def test_source_hash_stable():
    assert source_hash("abc") == source_hash("abc")
    assert source_hash("abc") != source_hash("abd")


def test_empty_text():
    assert extract_keys_from_text("") == []
