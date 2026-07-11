"""Activity search: type/outcome/id only; never body or subject."""

from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Customer, CustomerInteraction


def _seed(db):
    c = Customer(
        name="Act Cust",
        email="act@example.com",
        phone="5553300001",
        status="active",
    )
    db.session.add(c)
    db.session.flush()
    live = CustomerInteraction(
        customer_id=c.id,
        interaction_type="call",
        subject="SECRET SUBJECT DO NOT SEARCH",
        body="SECRET BODY WITH SSN 123-45-6789",
        outcome="completed",
        is_deleted=False,
    )
    deleted = CustomerInteraction(
        customer_id=c.id,
        interaction_type="call",
        subject="gone",
        body="gone body",
        outcome="completed",
        is_deleted=True,
    )
    email_ix = CustomerInteraction(
        customer_id=c.id,
        interaction_type="email",
        subject="x",
        body="y",
        outcome="no_answer",
    )
    db.session.add_all([live, deleted, email_ix])
    db.session.commit()
    return c, live, deleted, email_ix


def test_activity_search_flag_off_empty(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_ACTIVITY_SEARCH", "0")
    with app.app_context():
        from database import db

        _seed(db)
        req = parse_search_request(q="call", scope="activities", mode="full")
        result = unified_search_service.search(req)
        assert result["groups"].get("activities") == []


def test_activity_search_type_and_not_body(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_ACTIVITY_SEARCH", "1")
    with app.app_context():
        from database import db

        c, live, deleted, email_ix = _seed(db)
        req = parse_search_request(q="call", scope="activities", mode="full")
        result = unified_search_service.search(req)
        ids = {h["id"] for h in result["groups"]["activities"]}
        assert live.id in ids
        assert deleted.id not in ids
        assert email_ix.id not in ids
        # Body/subject secrets never appear in hit payload
        blob = str(result["groups"]["activities"])
        assert "SECRET BODY" not in blob
        assert "123-45-6789" not in blob
        assert "SECRET SUBJECT" not in blob


def test_activity_search_does_not_match_body_text(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_ACTIVITY_SEARCH", "1")
    with app.app_context():
        from database import db

        _seed(db)
        req = parse_search_request(
            q="SSN", scope="activities", mode="full"
        )
        result = unified_search_service.search(req)
        assert result["groups"].get("activities") == []


def test_default_scope_excludes_activities(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_ACTIVITY_SEARCH", "1")
    with app.app_context():
        from database import db

        _seed(db)
        req = parse_search_request(q="call", scope=None, mode="full")
        assert "activities" not in req.scopes
        result = unified_search_service.search(req)
        # may have empty activities key in groups but no hits required
        assert result["counts"].get("activities", 0) == 0
