import logging
from flask import jsonify
from .property_helpers import _wants_json, _safe_attr
from property_error_handlers import handle_property_errors, validate_property_id, require_property_exists, log_property_operation
from database import db
from services.database_service import database_service

# These functions will be imported and attached to the blueprint in the main properties.py file

def get_property_ai_history(property_id):
    """Get AI extraction history for a property"""
    history = database_service.get_ai_history(property_id)
    return jsonify([h.to_dict() for h in history])


def delete_property_ai_history(history_id):
    """Delete an AI extraction history record"""
    success = database_service.delete_ai_history(history_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to delete history"}), 400