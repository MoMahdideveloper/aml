"""Always-on rematch + agent notification behavior."""

import json
from unittest.mock import patch

from background_matcher import BackgroundMatcher, background_matcher
from celery_app import _rematch_queue_interval_seconds, get_celery_beat_schedule
from sqlalchemy_models import (
    Agent,
    AgentNotification,
    Customer,
    Property,
    PropertyMatch,
)


class TestAlwaysOnSchedule:
    def test_rematch_queue_default_is_60s(self, monkeypatch):
        monkeypatch.delenv("REMATCH_QUEUE_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("REMATCH_QUEUE_INTERVAL_MINUTES", raising=False)
        assert _rematch_queue_interval_seconds() == 60

    def test_rematch_queue_seconds_override(self, monkeypatch):
        monkeypatch.setenv("REMATCH_QUEUE_INTERVAL_SECONDS", "30")
        assert _rematch_queue_interval_seconds() == 30

    def test_beat_schedule_uses_faster_defaults(self, monkeypatch):
        monkeypatch.delenv("REMATCH_QUEUE_INTERVAL_SECONDS", raising=False)
        monkeypatch.delenv("REMATCH_QUEUE_INTERVAL_MINUTES", raising=False)
        monkeypatch.delenv("MATCHING_INTERVAL_MINUTES", raising=False)
        schedule = get_celery_beat_schedule()
        assert schedule["process-rematch-queue"]["schedule"] == 60
        assert schedule["run-property-matching"]["schedule"] == 15 * 60


class TestMatchNotifications:
    def test_new_match_creates_notification(self, app, db_setup):
        with app.app_context():
            agent = Agent(name="A1", email="a1@example.com", phone="1")
            db_setup.session.add(agent)
            db_setup.session.flush()

            customer = Customer(
                name="Buyer",
                email="b@example.com",
                phone="2",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=3,
                preferred_type="house",
                status="active",
            )
            prop = Property(
                title="Villa",
                address="1 Main",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1200,
                description="Nice",
                agent_id=agent.id,
                status="active",
            )
            db_setup.session.add_all([customer, prop])
            db_setup.session.commit()

            matcher = BackgroundMatcher()
            match = PropertyMatch(
                property_id=prop.id,
                customer_id=customer.id,
                agent_id=agent.id,
                match_score=0.88,
                confidence_level="high",
                priority="high",
                match_reasons=json.dumps(["Budget fit", "Bedrooms"]),
            )
            match._notify_kind = "new"
            match._previous_score = None
            db_setup.session.add(match)
            db_setup.session.commit()

            notes = matcher.create_agent_notifications([match])
            assert len(notes) == 1
            assert "New best match" in notes[0].title or "New property match" in notes[0].title
            assert notes[0].priority == "high"
            assert notes[0].status == "unread"

    def test_dedupe_unread_notification(self, app, db_setup):
        with app.app_context():
            agent = Agent(name="A2", email="a2@example.com", phone="1")
            db_setup.session.add(agent)
            db_setup.session.flush()
            customer = Customer(
                name="Buyer2",
                email="b2@example.com",
                phone="2",
                budget_min=100000,
                budget_max=200000,
                status="active",
            )
            prop = Property(
                title="Home",
                address="2 Main",
                price=160000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1100,
                description="Ok",
                agent_id=agent.id,
                status="active",
            )
            db_setup.session.add_all([customer, prop])
            db_setup.session.commit()

            match = PropertyMatch(
                property_id=prop.id,
                customer_id=customer.id,
                agent_id=agent.id,
                match_score=0.9,
                confidence_level="high",
                priority="high",
                match_reasons="[]",
            )
            match._notify_kind = "new"
            db_setup.session.add(match)
            db_setup.session.commit()

            matcher = BackgroundMatcher()
            first = matcher.create_agent_notifications([match])
            assert len(first) == 1

            match._notify_kind = "improved"
            match._previous_score = 0.8
            second = matcher.create_agent_notifications([match])
            assert second == []

    def test_save_marks_improved_only_on_delta(self, app, db_setup):
        with app.app_context():
            agent = Agent(name="A3", email="a3@example.com", phone="1")
            db_setup.session.add(agent)
            db_setup.session.flush()
            customer = Customer(
                name="Buyer3",
                email="b3@example.com",
                phone="3",
                budget_min=100000,
                budget_max=200000,
                status="active",
            )
            prop = Property(
                title="P3",
                address="3 Main",
                price=150000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1000,
                description="x",
                agent_id=agent.id,
                status="active",
            )
            db_setup.session.add_all([customer, prop])
            db_setup.session.commit()

            matcher = BackgroundMatcher()
            base = {
                "property_id": prop.id,
                "customer_id": customer.id,
                "agent_id": agent.id,
                "match_score": 0.80,
                "confidence_level": "high",
                "priority": "normal",
                "match_reasons": "[]",
                "property": prop,
                "customer": customer,
            }
            saved = matcher.save_matches_to_database([base])
            assert len(saved) == 1
            assert getattr(saved[0], "_notify_kind") == "new"

            tiny = dict(base, match_score=0.82)  # < 0.05 delta default
            saved2 = matcher.save_matches_to_database([tiny])
            assert len(saved2) == 1
            assert getattr(saved2[0], "_notify_kind") is None

            big = dict(base, match_score=0.90)
            saved3 = matcher.save_matches_to_database([big])
            assert len(saved3) == 1
            assert getattr(saved3[0], "_notify_kind") == "improved"
