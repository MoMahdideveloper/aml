"""Regression tests for crm.sync_property_embedding.

The Celery beat tick called this task once per property. When the Gemini API
returned 403, the provider handed back a non-semantic hash fallback, and the
task logged "Property embedding synced successfully" anyway -- so a run that
corrupted 197 Postgres rows looked healthy in the logs.

These tests pin two rules:
  1. A fallback vector is never written to property_embeddings.
  2. A degraded run never reports success.
"""

import json
from types import SimpleNamespace

import pytest

from database import db
from sqlalchemy_models import Property, PropertyEmbedding


def _make_property(title="Test Villa", address="1 Main St"):
    return Property(
        title=title,
        address=address,
        property_type="house",
        price=250000,
        bedrooms=3,
        status="active",
    )


def _fake_provider(vectors, fallback_indices):
    """Stand-in provider: no client, no network, no quota consumption."""
    return SimpleNamespace(
        embed=lambda texts: vectors,
        last_fallback_indices=set(fallback_indices),
        dimension=4,
    )


def _install_provider(monkeypatch, provider):
    """Patch every module that reads the provider singleton.

    vector_service imported the name directly, and the task re-imports it from
    services.embeddings to inspect last_fallback_indices, so both bindings must
    point at the same fake or the task reads real provider state.
    """
    monkeypatch.setattr("services.vector_service.embedding_provider", provider)
    monkeypatch.setattr("services.embeddings.embedding_provider", provider)


@pytest.fixture()
def sync_task():
    """The task body, not the bound Celery task.

    Calling the task object invokes FlaskContextTask.__call__, which pushes a
    fresh create_app() context backed by its own empty in-memory SQLite engine
    -- every query then fails with "no such table: properties". `.run` is the
    undecorated body, so the test's own app_context and seeded DB stay active.
    """
    from services.celery_tasks import sync_property_embedding_task

    return sync_property_embedding_task.run


class TestFallbackIsNeverPersisted:
    def test_degraded_run_writes_nothing(self, db_setup, app, monkeypatch, sync_task):
        """The exact production failure: 403 -> fallback -> no DB write."""
        with app.app_context():
            prop = _make_property()
            db.session.add(prop)
            db.session.commit()
            prop_id = prop.id

            _install_provider(monkeypatch, _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}))

            result = sync_task(prop_id)

            assert PropertyEmbedding.query.filter_by(property_id=prop_id).first() is None
            assert result["status"] == "skipped_degraded"

    def test_degraded_run_does_not_report_success(self, db_setup, app, monkeypatch, sync_task):
        """A corrupting run must not look healthy to whoever reads the logs."""
        with app.app_context():
            prop = _make_property(title="Log Check", address="2 Main St")
            db.session.add(prop)
            db.session.commit()

            _install_provider(monkeypatch, _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}))

            result = sync_task(prop.id)

            assert result["status"] != "upserted"

    def test_existing_good_row_is_left_untouched(self, db_setup, app, monkeypatch, sync_task):
        """A later outage must not overwrite an already-good vector."""
        with app.app_context():
            prop = _make_property(title="Has Good Row", address="3 Main St")
            db.session.add(prop)
            db.session.commit()
            prop_id = prop.id

            real = [1.0, 0.0, 0.0, 0.0]
            _install_provider(monkeypatch, _fake_provider([real], set()))
            assert sync_task(prop_id)["status"] == "upserted"

            stored = PropertyEmbedding.query.filter_by(property_id=prop_id).first()
            good_hash = stored.source_hash

            # Provider degrades and the property text changes, so the source_hash
            # cache no longer short-circuits and embed() is actually called.
            prop.title = "Has Good Row (renamed)"
            db.session.commit()
            _install_provider(monkeypatch, _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}))

            assert sync_task(prop_id)["status"] == "skipped_degraded"

            stored = PropertyEmbedding.query.filter_by(property_id=prop_id).first()
            assert json.loads(stored.embedding_data) == real
            assert stored.source_hash == good_hash


class TestHealthyPathStillWorks:
    def test_real_vector_is_persisted_and_reports_success(self, db_setup, app, monkeypatch, sync_task):
        with app.app_context():
            prop = _make_property(title="Healthy", address="4 Main St")
            db.session.add(prop)
            db.session.commit()
            prop_id = prop.id

            real = [0.0, 1.0, 0.0, 0.0]
            _install_provider(monkeypatch, _fake_provider([real], set()))

            result = sync_task(prop_id)

            assert result["status"] == "upserted"
            stored = PropertyEmbedding.query.filter_by(property_id=prop_id).first()
            assert stored is not None
            assert json.loads(stored.embedding_data) == real

    def test_property_is_retried_after_provider_recovers(self, db_setup, app, monkeypatch, sync_task):
        """The payoff for skipping: the row is still embeddable later."""
        with app.app_context():
            prop = _make_property(title="Recovers", address="5 Main St")
            db.session.add(prop)
            db.session.commit()
            prop_id = prop.id

            _install_provider(monkeypatch, _fake_provider([[0.5, 0.5, 0.5, 0.5]], {0}))
            sync_task(prop_id)
            assert PropertyEmbedding.query.filter_by(property_id=prop_id).first() is None

            real = [0.0, 0.0, 1.0, 0.0]
            _install_provider(monkeypatch, _fake_provider([real], set()))
            assert sync_task(prop_id)["status"] == "upserted"

            stored = PropertyEmbedding.query.filter_by(property_id=prop_id).first()
            assert stored is not None
            assert json.loads(stored.embedding_data) == real
