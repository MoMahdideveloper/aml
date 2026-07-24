import os
import sys
import types

import pytest

# Use in-memory SQLite for tests and avoid touching local files
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# Keep Celery tests hermetic; no local Redis service is required for unit tests.
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
# Most legacy tests hit CRM routes without login. Force default-deny off for the
# session-scoped app (setdefault is not enough if the shell already exported 1).
# Security tests that need deny rebuild the app after monkeypatch.setenv(...="1").
os.environ["AUTH_DEFAULT_DENY_ENABLED"] = "0"


# Provide a lightweight stub to prevent heavy vector service initialization
if "vector_service" not in sys.modules:
    stub = types.ModuleType("vector_service")

    class _DummyCollection:
        def count(self):
            return 0

    class _DummyVectorService:
        def __init__(self):
            self.properties_collection = _DummyCollection()
            self.customers_collection = _DummyCollection()

        def index_properties(self, *_, **__):
            return True

    stub.vector_service = _DummyVectorService()
    sys.modules["vector_service"] = stub

# Stub Gemini service to avoid importing google-genai during tests
if "gemini_service" not in sys.modules:
    gstub = types.ModuleType("gemini_service")

    class _DummyGeminiService:
        def get_property_recommendations(self, *_, **__):
            return []

        def extract_property_from_text(self, *_):
            return {"entity": "property", "data": {}, "missing": [], "confidence": 0.0}

        def extract_customer_from_text(self, *_):
            return {"entity": "customer", "data": {}, "missing": [], "confidence": 0.0}

    gstub.gemini_service = _DummyGeminiService()
    sys.modules["gemini_service"] = gstub


@pytest.fixture(scope="session")
def app():
    from app import create_app

    # Build a fresh factory app instead of reusing app.py's module-global app.
    # Migration tests intentionally import create_app under isolated env vars;
    # reusing the module-global instance would leak those settings here.
    flask_app = create_app(
        {
            "TESTING": True,
            "AUTH_DEFAULT_DENY_ENABLED": False,
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Ensure session-scoped app stays open for legacy CRM tests even if the
    # process imported create_app while AUTH_DEFAULT_DENY_ENABLED was on.
    flask_app.config.update(
        TESTING=True,
        AUTH_DEFAULT_DENY_ENABLED=False,
        WTF_CSRF_ENABLED=False,
    )
    return flask_app


@pytest.fixture()
def client(app):
    import sqlalchemy_models  # noqa: F401 — registers all ORM metadata
    from database import db

    with app.app_context():
        db.create_all()  # idempotent; restores tables after any db_setup teardown
    return app.test_client()


@pytest.fixture()
def db_setup(app):
    # Ensure models are imported and tables are created for each test
    import sqlalchemy_models  # noqa: F401
    from database import db

    with app.app_context():
        db.drop_all()
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def sample_data(db_setup, app):
    """
    Shared test data fixture for template and integration tests.
    Creates minimal Agent, Property, and Customer records.
    Returns eagerly-loaded dict copies to avoid DetachedInstanceError.
    """
    from sqlalchemy_models import Agent, Property, Customer
    from database import db

    with app.app_context():
        # Create agent (only required fields)
        agent = Agent(
            name="Test Agent",
            email="agent@test.com",
            phone="555-1234"
        )
        db.session.add(agent)
        db.session.flush()

        # Create property (only required fields)
        property_obj = Property(
            title="Luxury Villa",
            address="123 Main Street",
            price=500000,
            listing_type="sale",
            property_type="villa",
            bedrooms=4,
            bathrooms=3
        )
        db.session.add(property_obj)
        db.session.flush()

        # Create customer (only required fields)
        customer = Customer(
            name="John Doe",
            email="john@example.com",
            phone="555-5678"
        )
        db.session.add(customer)
        db.session.flush()

        db.session.commit()

        # Eagerly load all attributes before leaving app context
        agent_data = {
            'id': agent.id,
            'name': agent.name,
            'email': agent.email,
            'phone': agent.phone
        }

        property_data = {
            'id': property_obj.id,
            'title': property_obj.title,
            'address': property_obj.address,
            'price': property_obj.price
        }

        customer_data = {
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone
        }

        # Return plain dicts to avoid DetachedInstanceError
        # Keep both ORM objects and dict copies for compatibility
        db.session.expunge_all()  # Detach all objects from session

        return {
            'agent': agent,
            'property': property_obj,
            'customer': customer,
            'customers': [customer_data],
            'properties': [property_data]
        }
