"""Tests for VectorService.index_properties cache hygiene.

index_properties skips any property whose stored source_hash already matches the
current text. A non-semantic fallback vector hashes exactly like a real one, so
persisting a fallback poisons that cache permanently: the row looks embedded and
is never retried, even after the provider recovers. These tests pin the rule that
degraded vectors are never written.
"""

import json
from types import SimpleNamespace

from database import db
from services.vector_service import VectorService
from sqlalchemy_models import Property, PropertyEmbedding


def _make_property(title, address):
    return Property(
        title=title,
        address=address,
        property_type="house",
        price=250000,
        bedrooms=3,
    )


def _fake_provider(vectors, fallback_indices):
    """Stand-in provider: no client, no network, no quota consumption."""
    return SimpleNamespace(
        embed=lambda texts: vectors,
        last_fallback_indices=set(fallback_indices),
        dimension=4,
    )


class TestFallbackVectorsAreNotPersisted:
    def test_pure_fallback_batch_writes_nothing(self, db_setup, app, monkeypatch):
        with app.app_context():
            prop = _make_property("A", "1 Main St")
            db.session.add(prop)
            db.session.commit()

            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}),
            )

            assert VectorService().index_properties([prop]) is True
            assert PropertyEmbedding.query.count() == 0

    def test_partial_outage_stores_only_real_vectors(self, db_setup, app, monkeypatch):
        with app.app_context():
            good = _make_property("Good", "1 Main St")
            bad = _make_property("Bad", "2 Main St")
            db.session.add_all([good, bad])
            db.session.commit()
            good_id, bad_id = good.id, bad.id

            real = [1.0, 0.0, 0.0, 0.0]
            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                _fake_provider([real, [0.5, 0.5, 0.5, 0.5]], {1}),
            )

            assert VectorService().index_properties([good, bad]) is True

            assert PropertyEmbedding.query.count() == 1
            stored = PropertyEmbedding.query.filter_by(property_id=good_id).first()
            assert stored is not None
            assert json.loads(stored.embedding_data) == real
            assert PropertyEmbedding.query.filter_by(property_id=bad_id).first() is None

    def test_skipped_property_is_retried_after_recovery(self, db_setup, app, monkeypatch):
        """The real payoff: a row skipped during an outage still gets embedded later."""
        with app.app_context():
            prop = _make_property("A", "1 Main St")
            db.session.add(prop)
            db.session.commit()
            prop_id = prop.id
            service = VectorService()

            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}),
            )
            service.index_properties([prop])
            assert PropertyEmbedding.query.count() == 0

            real = [0.0, 1.0, 0.0, 0.0]
            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                _fake_provider([real], set()),
            )
            service.index_properties([prop])

            stored = PropertyEmbedding.query.filter_by(property_id=prop_id).first()
            assert stored is not None
            assert json.loads(stored.embedding_data) == real

    def test_skip_is_logged_as_a_warning(self, db_setup, app, monkeypatch):
        """Swap the logger for a recorder.

        Handler- and caplog-based capture both rely on shared logging state
        (levels, propagation, logging.disable) that other suites in the full run
        mutate. Replacing the instance's logger asserts the call directly.
        """
        with app.app_context():
            prop = _make_property("A", "1 Main St")
            db.session.add(prop)
            db.session.commit()

            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}),
            )

            warnings: list[str] = []
            service = VectorService()
            service.logger = SimpleNamespace(
                warning=lambda msg, *args: warnings.append(msg % args if args else msg),
                info=lambda *a, **k: None,
                debug=lambda *a, **k: None,
                error=lambda *a, **k: None,
            )

            service.index_properties([prop])

            assert any("skipped 1 degraded" in message for message in warnings), warnings

    def test_healthy_batch_is_unaffected(self, db_setup, app, monkeypatch):
        with app.app_context():
            first = _make_property("A", "1 Main St")
            second = _make_property("B", "2 Main St")
            db.session.add_all([first, second])
            db.session.commit()

            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                _fake_provider([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], set()),
            )

            assert VectorService().index_properties([first, second]) is True
            assert PropertyEmbedding.query.count() == 2

    def test_provider_without_the_attribute_still_works(self, db_setup, app, monkeypatch):
        """Back-compat: a provider that never reports fallbacks behaves as before."""
        with app.app_context():
            prop = _make_property("A", "1 Main St")
            db.session.add(prop)
            db.session.commit()

            monkeypatch.setattr(
                "services.vector_service.embedding_provider",
                SimpleNamespace(embed=lambda texts: [[1.0, 0.0, 0.0, 0.0]], dimension=4),
            )

            assert VectorService().index_properties([prop]) is True
            assert PropertyEmbedding.query.count() == 1
