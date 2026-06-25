import os

import pytest

from services.environment_service import EnvironmentService
from sqlalchemy_models import EnvironmentVariable


def test_protected_env_key_rejected_for_create(app, db_setup):
    with app.app_context():
        service = EnvironmentService()
        with pytest.raises(ValueError, match="policy violation"):
            service.create_variable("DATABASE_URL", "postgresql://example")


def test_protected_env_key_rejected_for_update_and_delete(app, db_setup):
    with app.app_context():
        service = EnvironmentService()
        var = EnvironmentVariable(key="SESSION_SECRET", value="secret", is_sensitive=True, is_required=False)
        db_setup.session.add(var)
        db_setup.session.commit()

        with pytest.raises(ValueError, match="policy violation"):
            service.update_variable("SESSION_SECRET", "next-secret")

        with pytest.raises(ValueError, match="policy violation"):
            service.delete_variable("SESSION_SECRET")


def test_apply_all_to_runtime_skips_protected_keys(app, db_setup, monkeypatch):
    with app.app_context():
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("BUSINESS_FLAG", raising=False)

        service = EnvironmentService()
        db_setup.session.add(EnvironmentVariable(key="DATABASE_URL", value="postgresql://prod"))
        db_setup.session.add(EnvironmentVariable(key="BUSINESS_FLAG", value="1"))
        db_setup.session.commit()

        applied_count, errors = service.apply_all_to_runtime()

        assert applied_count == 1
        assert any("Skipped DATABASE_URL" in item for item in errors)
        assert os.environ.get("BUSINESS_FLAG") == "1"

