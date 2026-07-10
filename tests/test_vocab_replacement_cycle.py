"""Replacement cycle rejection."""

from services.vocab.service import VocabError, vocab_service


def test_cycle_rejected(db_setup, app):
    with app.app_context():
        vocab_service.create_replacement("apt", "apartment")
        try:
            vocab_service.create_replacement("apartment", "apt")
            assert False, "expected cycle error"
        except VocabError as e:
            assert e.code == "cycle"


def test_chain_cycle_rejected(db_setup, app):
    with app.app_context():
        vocab_service.create_replacement("a", "b")
        vocab_service.create_replacement("b", "c")
        try:
            vocab_service.create_replacement("c", "a")
            assert False, "expected cycle"
        except VocabError as e:
            assert e.code == "cycle"
