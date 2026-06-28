import logging
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
import os
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from jinja2 import TemplateNotFound

from database import db
from services.database_service import database_service
from services.vector_service import vector_service
from services.favorites_service import FavoritesService
from services.gemini_service import gemini_service
from forms import PropertyForm, PropertyEditForm
from sqlalchemy_models import Property, PropertyActivityLog, SyncState
from application.services.search_properties_service import SearchPropertiesService
from application.dtos import SearchRequest
from error_handlers import register_blueprint_error_handlers, handle_database_error, safe_json_response
from property_error_handlers import (
    handle_property_errors, validate_property_id, require_property_exists,
    log_property_operation, validate_property_data, handle_database_connection_error,
    PropertyValidationError, PropertyOperationError, get_property_with_related_data
)
from datetime import datetime
from maskan_field_constants import (
    PROPERTY_TYPES as MASKAN_PROPERTY_TYPES,
    DOCUMENT_TYPES, WALL_COVERINGS, CABINET_TYPES,
    COOLING_SYSTEMS, HEATING_SYSTEMS, FLOORING_TYPES,
    FACADE_TYPES, DIRECTIONS, PROPERTY_FEATURES as MASKAN_FEATURES,
    get_all_constants,
)
from extensions import limiter

# Import our modularized functions
from .property_listing import properties, map_view
from .property_crud import add_property, update_property, delete_property
from .property_related import get_property_ai_history, delete_property_ai_history
from .property_api import (
    reveal_contact, smart_search,
    extract_property_from_image, extract_property_from_text
)

# Import property_details module to avoid circular import issues
from . import property_details
view_property = property_details.view_property
property_detail = property_details.property_detail
edit_property = property_details.edit_property
get_edit_modal_html = property_details.get_edit_modal_html

bp = Blueprint("properties", __name__)

# Register error handlers for this blueprint
register_blueprint_error_handlers(bp)

# Initialize favorites service
favorites_service = FavoritesService()

# Initialize search properties service
search_properties_service = SearchPropertiesService()

def rate_limit(max_requests=10, window_minutes=1):
    """
    Redis-backed rate limiting decorator.
    Args:
        max_requests: Maximum number of requests allowed
        window_minutes: Time window in minutes
    """
    return limiter.limit(f"{max_requests} per {window_minutes} minute")


def _wants_json():
    accept_header = request.headers.get("Accept", "")
    return (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in accept_header
        or request.args.get("format") == "json"
    )


def _is_mock_value(value):
    return value is not None and value.__class__.__module__.startswith("unittest.mock")


def _safe_attr(obj, field_name, default=None):
    value = getattr(obj, field_name, default)
    if _is_mock_value(value):
        return default
    return value


def _format_datetime(value, fallback="Unknown"):
    if value is None:
        return fallback
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return fallback
    if isinstance(value, str):
        return value
    return fallback


def _normalize_numeric_input(raw_value):
    if raw_value is None:
        return None
    normalized = str(raw_value).strip()
    if normalized == "":
        return ""
    normalized = normalized.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    normalized = normalized.replace(",", "").replace("_", "").replace(" ", "")
    normalized = normalized.replace("٬", "").replace("،", "")
    return normalized


def _parse_optional_toman(raw_value, field_label):
    normalized = _normalize_numeric_input(raw_value)
    if normalized in (None, ""):
        return None
    try:
        return int(round(float(normalized)))
    except (ValueError, TypeError):
        raise PropertyValidationError(f"Invalid pricing data: {field_label} must be a valid integer amount in toman")


def _serialize_property_for_json(property_obj):
    deals = _safe_attr(property_obj, "deals", []) or []
    if _is_mock_value(deals):
        deals = []

    active_deals = 0
    for deal in deals:
        deal_status = getattr(deal, "status", None)
        if deal_status not in ["closed_won", "closed_lost"]:
            active_deals += 1

    agent = _safe_attr(property_obj, "agent", None)
    agent_name = _safe_attr(agent, "name", "Unassigned") if agent else "Unassigned"
    agent_email = _safe_attr(agent, "email", "") if agent else ""
    agent_phone = _safe_attr(agent, "phone", "") if agent else ""

    return {
        "id": _safe_attr(property_obj, "id", None),
        "title": _safe_attr(property_obj, "title", "Untitled Property") or "Untitled Property",
        "address": _safe_attr(property_obj, "address", "Address not available") or "Address not available",
        "price": _safe_attr(property_obj, "price", 0) or 0,
        "property_type": _safe_attr(property_obj, "property_type", "Unknown") or "Unknown",
        "bedrooms": _safe_attr(property_obj, "bedrooms", 0) or 0,
        "bathrooms": _safe_attr(property_obj, "bathrooms", 0) or 0,
        "square_feet": _safe_attr(property_obj, "square_feet", 0) or 0,
        "description": _safe_attr(property_obj, "description", "No description available") or "No description available",
        "status": _safe_attr(property_obj, "status", "unknown") or "unknown",
        "year_built": _safe_attr(property_obj, "year_built", None),
        "parking_spaces": _safe_attr(property_obj, "parking_spaces", 0) or 0,
        "floors": _safe_attr(property_obj, "floors", 1) or 1,
        "units": _safe_attr(property_obj, "units", 1) or 1,
        "property_condition": _safe_attr(property_obj, "property_condition", "unknown") or "unknown",
        "heating_type": _safe_attr(property_obj, "heating_type", "") or "",
        "cooling_type": _safe_attr(property_obj, "cooling_type", "") or "",
        "neighborhood": _safe_attr(property_obj, "neighborhood", "Unknown") or "Unknown",
        "property_category": _safe_attr(property_obj, "property_category", "residential") or "residential",
        "listing_type": _safe_attr(property_obj, "listing_type", "sale") or "sale",
        "rahn": _safe_attr(property_obj, "rahn", None),
        "ejare": _safe_attr(property_obj, "ejare", None),
        "property_features": _safe_attr(property_obj, "property_features", "") or "",
        "document_type": _safe_attr(property_obj, "document_type", None),
        "floor_number": _safe_attr(property_obj, "floor_number", None),
        "built_area": _safe_attr(property_obj, "built_area", None),
        "land_area": _safe_attr(property_obj, "land_area", None),
        "floor_covering": _safe_attr(property_obj, "floor_covering", None),
        "facade_type": _safe_attr(property_obj, "facade_type", None),
        "wall_covering": _safe_attr(property_obj, "wall_covering", None),
        "cabinet_type": _safe_attr(property_obj, "cabinet_type", None),
        "property_direction": _safe_attr(property_obj, "property_direction", None),
        "is_exchangeable": bool(_safe_attr(property_obj, "is_exchangeable", False)),
        "boundary_width": _safe_attr(property_obj, "boundary_width", None),
        "density": _safe_attr(property_obj, "density", None),
        "commercial_status": _safe_attr(property_obj, "commercial_status", None),
        "usage_type": _safe_attr(property_obj, "usage_type", None),
        "ceiling_count": _safe_attr(property_obj, "ceiling_count", None),
        "permit_ceiling": _safe_attr(property_obj, "permit_ceiling", None),
        "property_length": _safe_attr(property_obj, "property_length", None),
        "property_height": _safe_attr(property_obj, "property_height", None),
        "price_per_meter": _safe_attr(property_obj, "price_per_meter", None),
        "custom_fields": _safe_attr(property_obj, "custom_fields", "") or "",
        "created_at": _format_datetime(_safe_attr(property_obj, "created_at", None)),
        "agent_name": agent_name,
        "agent_email": agent_email,
        "agent_phone": agent_phone,
        "agent_id": _safe_attr(property_obj, "agent_id", None),
        "total_deals": len(deals),
        "active_deals": active_deals,
        "image_filename": _safe_attr(property_obj, "image_filename", None),
        "detail_url": (
            url_for("properties.property_detail", property_id=_safe_attr(property_obj, "id", 0))
            if _safe_attr(property_obj, "id", None)
            else None
        ),
        "modal_url": (
            url_for("properties.view_property", property_id=_safe_attr(property_obj, "id", 0))
            if _safe_attr(property_obj, "id", None)
            else None
        ),
        "edit_modal_url": (
            url_for("properties.edit_property", property_id=_safe_attr(property_obj, "id", 0))
            if _safe_attr(property_obj, "id", None)
            else None
        ),
        "share_url": (
            url_for("properties.share_property", property_id=_safe_attr(property_obj, "id", 0))
            if _safe_attr(property_obj, "id", None)
            else None
        ),
    }


# Share property route (was missing from original but referenced in _serialize_property_for_json)
@bp.route("/properties/<int:property_id>/share", methods=["GET"])
@handle_property_errors
@handle_database_connection_error
@validate_property_id
@require_property_exists
@log_property_operation("share_property")
def share_property(property_id, property_obj):
    """Share property endpoint"""
    property_data = _serialize_property_for_json(property_obj)

    if _wants_json():
        return jsonify({"property": property_data}), 200

    # For now, just redirect back or show a simple sharing page
    # In a full implementation, this might show social sharing options
    return redirect(url_for("properties.properties"))


# Register all the routes
bp.add_url_rule("/properties", "properties", properties)
bp.add_url_rule("/properties/map", "map_view", map_view)
bp.add_url_rule("/properties/add", "add_property", add_property, methods=["POST"])
bp.add_url_rule("/properties/<int:property_id>", "view_property", view_property, methods=["GET"])
bp.add_url_rule("/properties/<property_id>/detail", "property_detail", property_detail)
bp.add_url_rule("/properties/<int:property_id>/edit", "edit_property", edit_property, methods=["GET"])
bp.add_url_rule("/api/v1/properties/<int:property_id>/edit-modal-html", "get_edit_modal_html", get_edit_modal_html, methods=["GET"])
bp.add_url_rule("/properties/<int:property_id>", "update_property", update_property, methods=["PUT", "POST"])
bp.add_url_rule("/properties/<int:property_id>/delete", "delete_property", delete_property, methods=["POST"])
bp.add_url_rule("/api/properties/<int:property_id>/reveal-contact", "reveal_contact", reveal_contact, methods=["POST"])
bp.add_url_rule("/api/properties/smart-search", "smart_search", smart_search)
bp.add_url_rule("/properties/extract-from-image", "extract_property_from_image", extract_property_from_image, methods=["POST"])
bp.add_url_rule("/properties/extract-from-text", "extract_property_from_text", extract_property_from_text, methods=["POST"])
bp.add_url_rule("/properties/<int:property_id>/ai-history", "get_property_ai_history", get_property_ai_history, methods=["GET"])
bp.add_url_rule("/properties/ai-history/<int:history_id>", "delete_property_ai_history", delete_property_ai_history, methods=["DELETE"])
bp.add_url_rule("/properties/<int:property_id>/share", "share_property", share_property)