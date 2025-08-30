import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()


def init_db(app):
    """Initialize database with Flask app"""
    # Configure database URI
    if os.environ.get("DATABASE_URL"):
        # Production - use PostgreSQL
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    else:
        # Development - use SQLite
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///real_estate_crm.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    return db
