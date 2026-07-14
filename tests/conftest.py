import os
import sys
import types

import pytest

# Use in-memory SQLite for tests and avoid touching local files
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
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
    from app import app as flask_app

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
