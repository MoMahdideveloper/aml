"""Related terms are not synonyms for expansion."""

from services.vocab.expand import expand_query_terms
from services.vocab.service import vocab_service


def test_related_not_in_expand(db_setup, app):
    with app.app_context():
        term = vocab_service.create_term("luxury")
        vocab_service.add_related(term.id, "premium")
        # expand maps only from synonym_groups — related not loaded there
        keys = expand_query_terms("luxury", synonym_groups={"luxury": ["luxury"]})
        assert "premium" not in keys
