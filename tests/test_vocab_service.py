"""Vocab service CRUD + cache invalidate."""

from services.vocab.lexicon import invalidate_lexicon_cache, load_lexicon_maps
from services.vocab.service import VocabError, vocab_service


def test_create_term_and_synonym(db_setup, app):
    with app.app_context():
        invalidate_lexicon_cache()
        term = vocab_service.create_term("Villa")
        assert term.normalized_key == "villa"
        syn = vocab_service.add_synonym(term.id, "House")
        assert syn.synonym_key == "house"
        replacements, groups = load_lexicon_maps(force=True)
        assert "villa" in groups
        assert "house" in groups["villa"]


def test_duplicate_term_rejected(db_setup, app):
    with app.app_context():
        vocab_service.create_term("Condo")
        try:
            vocab_service.create_term("condo")
            assert False, "expected VocabError"
        except VocabError as e:
            assert e.code == "duplicate"


def test_replacement_and_archive(db_setup, app):
    with app.app_context():
        invalidate_lexicon_cache()
        row = vocab_service.create_replacement("sqm", "square meters", priority=5)
        assert row.from_key == "sqm"
        replacements, _ = load_lexicon_maps(force=True)
        assert replacements.get("sqm") == "square meters"
        vocab_service.archive_replacement(row.id)
        replacements2, _ = load_lexicon_maps(force=True)
        assert "sqm" not in replacements2


def test_synonym_same_as_term_rejected(db_setup, app):
    with app.app_context():
        term = vocab_service.create_term("apartment")
        try:
            vocab_service.add_synonym(term.id, "Apartment")
            assert False, "expected VocabError"
        except VocabError as e:
            assert e.code == "same_as_term"
