from __future__ import annotations

import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

from tests.schema_parity import orm_schema_gaps


def test_orm_schema_gaps_unit_contract():
    metadata = sa.MetaData()
    sa.Table(
        "present",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("required_name", sa.String(40)),
    )
    sa.Table("missing", metadata, sa.Column("id", sa.Integer, primary_key=True))

    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE present (id INTEGER PRIMARY KEY)")
        connection.exec_driver_sql("ALTER TABLE present ADD COLUMN db_only TEXT")

    assert orm_schema_gaps(engine, metadata) == {
        "missing_tables": ["missing"],
        "missing_columns": {"present": ["required_name"]},
    }


def test_heads_have_zero_orm_schema_gaps(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'migration.sqlite').as_posix()}")
    monkeypatch.setenv("EVENT_HANDLERS_ENABLED", "0")

    from app import create_app
    from database import db
    from flask_migrate import upgrade
    import sqlalchemy_models  # noqa: F401 - registers all mapped models

    app = create_app({"TESTING": True})
    try:
        with app.app_context():
            upgrade(revision="heads")
            gaps = orm_schema_gaps(db.engine, db.metadata)

        assert gaps == {
            "missing_tables": [],
            "missing_columns": {},
        }
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_reconciliation_revision_has_canonical_parent():
    config = Config()
    config.set_main_option("script_location", str(Path("migrations").resolve()))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == ["d4e5f6a7b8c9"]
    assert scripts.get_revision("d4e5f6a7b8c9").down_revision == "c3d4e5f6a7b8"
    assert all(revision.revision != "a2b3c4d5e6f7" for revision in scripts.walk_revisions())


def test_existing_partial_table_is_completed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'partial.sqlite').as_posix()}")
    monkeypatch.setenv("EVENT_HANDLERS_ENABLED", "0")

    from app import create_app
    from database import db
    from flask_migrate import upgrade
    import sqlalchemy_models  # noqa: F401 - registers all mapped models

    app = create_app({"TESTING": True})
    try:
        with app.app_context():
            upgrade(revision="a0b1c2d3e4f5")
            with db.engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE property_images "
                    "(id INTEGER PRIMARY KEY, property_id INTEGER NOT NULL)"
                )
            upgrade(revision="heads")

            gaps = orm_schema_gaps(db.engine, db.metadata)
            physical_columns = {
                column["name"]
                for column in sa.inspect(db.engine).get_columns("property_images")
            }
            expected_columns = {
                column.name for column in db.metadata.tables["property_images"].columns
            }

        assert gaps["missing_tables"] == []
        assert gaps["missing_columns"] == {}
        assert physical_columns == expected_columns
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
