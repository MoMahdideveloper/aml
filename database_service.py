"""Compatibility shim — use services.database_service in new code."""
from services.database_service import DatabaseService, database_service

__all__ = ["DatabaseService", "database_service"]
