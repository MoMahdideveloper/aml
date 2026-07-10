"""Search repository + service integration."""

from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Agent, Customer, Property, Task


def test_customer_exact_email_and_prefix(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Ada Lovelace",
                email="ada@example.com",
                phone="5551000001",
                status="active",
            )
        )
        db.session.add(
            Customer(
                name="Bob Builder",
                email="bob@example.com",
                phone="5551000002",
                status="active",
            )
        )
        db.session.commit()

        req = parse_search_request(q="ada@example.com", scope="customers", mode="full")
        result = unified_search_service.search(req)
        assert result["total_count"] >= 1
        titles = [h["title"] for h in result["groups"]["customers"]]
        assert "Ada Lovelace" in titles

        req2 = parse_search_request(q="Ada", scope="customers")
        r2 = unified_search_service.search(req2)
        assert any(h["title"] == "Ada Lovelace" for h in r2["groups"]["customers"])


def test_property_file_code_exact(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Villa One",
                address="1 Sea Rd",
                property_type="villa",
                price=100,
                file_code="FC-SEARCH-1",
            )
        )
        db.session.commit()
        req = parse_search_request(q="FC-SEARCH-1", scope="properties")
        result = unified_search_service.search(req)
        assert result["total_count"] == 1
        assert result["groups"]["properties"][0]["matched_field"] in (
            "file_code",
            "exact",
            "id",
        )


def test_soft_deleted_excluded(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Gone Person",
                email="gone@example.com",
                phone="5551000099",
                is_deleted=True,
            )
        )
        db.session.commit()
        req = parse_search_request(q="Gone", scope="customers")
        result = unified_search_service.search(req)
        assert result["total_count"] == 0


def test_deterministic_order(db_setup, app):
    with app.app_context():
        from database import db

        for i, name in enumerate(["Alpha Match", "Alpha Match B", "Beta Other"]):
            db.session.add(
                Customer(
                    name=name,
                    email=f"ord{i}@example.com",
                    phone=f"555200000{i}",
                )
            )
        db.session.commit()
        req = parse_search_request(q="Alpha", scope="customers", sort="relevance")
        r1 = unified_search_service.search(req)
        r2 = unified_search_service.search(req)
        ids1 = [h["id"] for h in r1["groups"]["customers"]]
        ids2 = [h["id"] for h in r2["groups"]["customers"]]
        assert ids1 == ids2


def test_grouped_mixed(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(name="Mixed Cust", email="mixc@example.com", phone="5553000001")
        )
        db.session.add(
            Property(
                title="Mixed Prop",
                address="9 Mix St",
                property_type="apt",
                price=1,
            )
        )
        ag = Agent(
            name="Mixed Agent",
            email="mixa@example.com",
            phone="5553000002",
        )
        db.session.add(ag)
        db.session.flush()
        db.session.add(
            Task(title="Mixed Task", agent_id=ag.id, status="pending", priority="low")
        )
        db.session.commit()
        req = parse_search_request(q="Mixed")
        result = unified_search_service.search(req)
        assert result["counts"]["customers"] >= 1
        assert result["counts"]["properties"] >= 1
        assert result["counts"]["agents"] >= 1
        assert result["counts"]["tasks"] >= 1
