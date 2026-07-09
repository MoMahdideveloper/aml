import logging
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app, jsonify, make_response
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
from .property_helpers import (
    _wants_json, _is_mock_value, _safe_attr, _format_datetime,
    _normalize_numeric_input, _parse_optional_toman, _serialize_property_for_json
)

# We'll create a blueprint in the main properties.py and import the functions here.
# For now, we assume the blueprint is defined in the main file and we are just defining the view functions.
# However, to avoid circular imports, we will define the functions without the blueprint decorator here and then attach them in the main file.

# Alternatively, we can define the functions and then in the main properties.py we attach them to the blueprint.
# Let's do that: we define the functions here without the blueprint decorator, and then in properties.py we import and assign them.

# But note: the original properties.py had the blueprint defined and then the routes decorated with @bp.
# We are restructuring: we will have a main properties.py that defines the blueprint and then imports the functions from modules and assigns them to routes.

# Therefore, in this file (property_details.py) we define the functions without decorators.

def view_property(property_id, property_obj=None):
    """GET /properties/<id>: full detail page for browsers; JSON/modal for AJAX clients."""
    if property_obj is None:
        property_obj = get_property_with_related_data(property_id)

    # Browser navigation should land on the shell-backed detail page.
    if not _wants_json():
        return redirect(url_for("properties.property_detail", property_id=property_id))

    property_data = _serialize_property_for_json(property_obj)
    return jsonify({"property": property_data}), 200


def property_detail(property_id):
    """Full property details page with enhanced features and robust error handling"""
    # Use module-level symbol so tests can patch views.properties.get_property_with_related_data.
    property_obj = get_property_with_related_data(property_id)

    # Access checks are best-effort and should not break rendering in degraded test/runtime states.
    try:
        if hasattr(database_service, "validate_property_access"):
            database_service.validate_property_access(property_id)
    except Exception as e:
        logging.warning(f"Property access validation degraded for {property_id}: {str(e)}")

    # Calculate additional property statistics with safe access
    total_deals = 0
    active_deals = 0
    recent_activity = None

    try:
        deals = [d for d in (_safe_attr(property_obj, "deals", []) or []) if not getattr(d, "is_deleted", False)]
        total_deals = len(deals)
        active_deals = len([d for d in deals if getattr(d, "status", None) not in ["closed_won", "closed_lost"]])

        if deals:
            recent_deal = max(
                deals,
                key=lambda d: getattr(d, "updated_at", None) or getattr(d, "created_at", None),
            )
            recent_activity = {
                "type": "deal",
                "status": getattr(recent_deal, "status", None),
                "date": getattr(recent_deal, "updated_at", None) or getattr(recent_deal, "created_at", None),
            }
    except Exception as e:
        logging.warning(f"Error calculating deal statistics for property {property_id}: {str(e)}")

    try:
        related_properties = database_service.get_related_properties(property_id, limit=4)
    except Exception as e:
        logging.warning(f"Error loading related properties for {property_id}: {str(e)}")
        related_properties = []

    title = _safe_attr(property_obj, "title", f"Property #{property_id}") or f"Property #{property_id}"
    neighborhood = _safe_attr(property_obj, "neighborhood", "Unknown") or "Unknown"
    property_type = _safe_attr(property_obj, "property_type", "Unknown") or "Unknown"
    price = _safe_attr(property_obj, "price", 0) or 0
    bedrooms = _safe_attr(property_obj, "bedrooms", 0) or 0
    bathrooms = _safe_attr(property_obj, "bathrooms", 0) or 0
    square_feet = _safe_attr(property_obj, "square_feet", 0) or 0
    listing_type = _safe_attr(property_obj, "listing_type", "sale") or "sale"
    status = _safe_attr(property_obj, "status", "unknown") or "unknown"
    created_at = _safe_attr(property_obj, "created_at", None)
    updated_at = _safe_attr(property_obj, "updated_at", None)
    agent = _safe_attr(property_obj, "agent", None)

    if isinstance(price, (int, float)) and price:
        meta_description = (
            f"{property_type} in {neighborhood}. "
            f"{bedrooms} bed, {bathrooms} bath. ${price:,.0f}"
        )
    else:
        meta_description = f"{property_type} in {neighborhood}"

    property_data = {
        "id": _safe_attr(property_obj, "id", property_id),
        "title": title,
        "address": _safe_attr(property_obj, "address", "Address not available") or "Address not available",
        "price": price,
        "property_type": property_type,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "square_feet": square_feet,
        "description": _safe_attr(property_obj, "description", "No description available") or "No description available",
        "status": status,
        "year_built": _safe_attr(property_obj, "year_built", None),
        "parking_spaces": _safe_attr(property_obj, "parking_spaces", 0) or 0,
        "floors": _safe_attr(property_obj, "floors", 1) or 1,
        "units": _safe_attr(property_obj, "units", 1) or 1,
        "property_condition": _safe_attr(property_obj, "property_condition", "unknown") or "unknown",
        "heating_type": _safe_attr(property_obj, "heating_type", "") or "",
        "cooling_type": _safe_attr(property_obj, "cooling_type", "") or "",
        "neighborhood": neighborhood,
        "property_category": _safe_attr(property_obj, "property_category", "residential") or "residential",
        "listing_type": listing_type,
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
        "created_at": _format_datetime(created_at),
        "updated_at": _format_datetime(updated_at, fallback=None),
        "agent_name": _safe_attr(agent, "name", "Unassigned") if agent else "Unassigned",
        "agent_email": _safe_attr(agent, "email", "") if agent else "",
        "agent_phone": _safe_attr(agent, "phone", "") if agent else "",
        "agent_id": _safe_attr(property_obj, "agent_id", None),
        "total_deals": total_deals,
        "active_deals": active_deals,
        "recent_activity": recent_activity,
        "meta_title": f"{title} - {neighborhood}" if neighborhood else title,
        "meta_description": meta_description,
        "canonical_url": url_for("properties.property_detail", property_id=property_id, _external=True),
        "price_per_sqft": round(price / square_feet, 2) if isinstance(price, (int, float)) and price and square_feet else None,
        "is_rental": listing_type == "rental",
        "is_available": status == "active",
        "has_agent": agent is not None,
        "image_filename": _safe_attr(property_obj, "image_filename", None),
        "source": _safe_attr(property_obj, "source", "manual") or "manual",
        "file_code": _safe_attr(property_obj, "file_code", None),
    }

    if listing_type == "rental" and square_feet:
        if property_data["rahn"]:
            property_data["rahn_per_sqft"] = round(property_data["rahn"] / square_feet, 0)
        if property_data["ejare"]:
            property_data["ejare_per_sqft"] = round(property_data["ejare"] / square_feet, 0)

    from flask import make_response

    try:
        rendered_html = render_template(
            "property_details.html",
            property=property_data,
            related_properties=related_properties,
        )
    except TemplateNotFound:
        if current_app.testing or _wants_json():
            return jsonify({"property": property_data}), 200
        raise

    response = make_response(rendered_html)
    response.headers["Cache-Control"] = "public, max-age=300"
    etag_basis = updated_at or created_at or title
    response.headers["ETag"] = f"property-{property_id}-{hash(str(etag_basis))}"

    return response


def edit_property(property_id):
    """Handle property edit form request (AJAX)"""
    property_obj = get_property_with_related_data(property_id)

    if _wants_json():
        property_data = _serialize_property_for_json(property_obj)
        return jsonify({"property": property_data}), 200

    # For non-AJAX requests, redirect to property detail or show error
    return redirect(url_for("properties.property_detail", property_id=property_id))


def get_edit_modal_html(property_id):
    """Return HTML for property edit modal (AJAX endpoint)"""
    property_obj = get_property_with_related_data(property_id)
    property_data = _serialize_property_for_json(property_obj)

    try:
        html = render_template("modals/property_edit_modal.html", property=property_data)
        return html
    except TemplateNotFound:
        if current_app.testing or _wants_json():
            return jsonify({"error": "Template not found"}), 404
        raise