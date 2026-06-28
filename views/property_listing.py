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


@bp.route("/properties")
def properties():
    # Create search request DTO from request arguments
    search_request = SearchRequest(
        query=request.args.get("search", ""),
        listing_type=request.args.get("listing_type", ""),
        status=request.args.get("status", ""),
        property_type=request.args.get("type", ""),
        property_category=request.args.get("category", ""),
        property_condition=request.args.get("condition", ""),
        neighborhood=request.args.get("neighborhood", ""),
        min_price=request.args.get("min_price", type=float),
        max_price=request.args.get("max_price", type=float),
        bedrooms=request.args.get("bedrooms", type=int),
        bathrooms=request.args.get("bathrooms", type=int),
        min_sqft=request.args.get("min_sqft", type=int),
        max_sqft=request.args.get("max_sqft", type=int),
        year_built_min=request.args.get("year_built_min", type=int),
        year_built_max=request.args.get("year_built_max", type=int),
        agent_id=request.args.get("agent_id", type=int),
        source=request.args.get("source", ""),
        page=request.args.get("page", default=1, type=int),
        per_page=request.args.get("per_page", default=10, type=int)
    )

    # Extract variables for template compatibility (to avoid changing the template)
    search_query = search_request.query
    listing_type = search_request.listing_type
    status = search_request.status
    property_type = search_request.property_type
    property_category = search_request.property_category
    property_condition = search_request.property_condition
    neighborhood = search_request.neighborhood
    min_price = search_request.min_price
    max_price = search_request.max_price
    bedrooms = search_request.bedrooms
    bathrooms = search_request.bathrooms
    min_sqft = search_request.min_sqft
    max_sqft = search_request.max_sqft
    year_built_min = search_request.year_built_min
    year_built_max = search_request.year_built_max
    agent_id = search_request.agent_id
    source = search_request.source
    page = search_request.page
    per_page = search_request.per_page

    # Search for properties using the service
    search_result = search_properties_service.search_properties(search_request)
    properties = search_result["items"]
    pagination = search_result["pagination"]

    agents = database_service.get_agents()
    property_types = sorted(
        v[0] for v in db.session.query(func.distinct(Property.property_type)).all() if v[0]
    )
    neighborhoods = sorted(
        v[0] for v in db.session.query(func.distinct(Property.neighborhood)).all() if v[0]
    )
    property_conditions = ["excellent", "good", "fair", "needs_renovation"]
    property_categories = ["residential", "commercial", "industrial"]
    listing_types = ["sale", "rental"]
    property_statuses = ["active", "pending", "sold", "rented", "archived"]

    for prop in properties:
        setattr(prop, "agent_name", prop.agent.name if prop.agent else "Unassigned")

    return render_template(
        "properties.html",
        properties=properties,
        form=PropertyForm(),
        agents=agents,
        property_types=property_types,
        neighborhoods=neighborhoods,
        property_conditions=property_conditions,
        property_categories=property_categories,
        listing_types=listing_types,
        property_statuses=property_statuses,
        pagination=pagination,
        page=page,
        per_page=per_page,
        search_query=search_query,
        listing_type=listing_type,
        status=status,
        property_type=property_type,
        property_category=property_category,
        property_condition=property_condition,
        neighborhood=neighborhood,
        min_price=min_price,
        max_price=max_price,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        min_sqft=min_sqft,
        max_sqft=max_sqft,
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        agent_id=agent_id,
        source=source,
        # Maskan field constants for dropdown selects
        maskan_property_types=MASKAN_PROPERTY_TYPES,
        document_types=DOCUMENT_TYPES,
        wall_coverings=WALL_COVERINGS,
        cabinet_types=CABINET_TYPES,
        cooling_systems=COOLING_SYSTEMS,
        heating_systems=HEATING_SYSTEMS,
        flooring_types=FLOORING_TYPES,
        facade_types=FACADE_TYPES,
        directions=DIRECTIONS,
        maskan_features=MASKAN_FEATURES,
    )


@bp.route("/properties/map")
def map_view():
    """Interactive map view of all properties with location data"""
    import json as _json
    all_properties = Property.query.filter(Property.is_deleted.is_(False)).all()
    properties_json = _json.dumps([
        {
            "id": p.id,
            "title": p.title,
            "address": p.address,
            "price": p.price,
            "property_type": p.property_type,
            "listing_type": p.listing_type,
            "rahn": p.rahn,
            "ejare": p.ejare,
            "bedrooms": p.bedrooms,
            "square_feet": p.square_feet,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "file_code": p.file_code,
            "has_elevator": p.has_elevator,
            "has_storage": p.has_storage,
            "image_filename": p.image_filename,
        }
        for p in all_properties
    ])
    return render_template("map_view.html", properties_json=properties_json)


@bp.route("/api/properties/smart-search")
def smart_search():
    """Semantic search for properties using vector embeddings"""
    query = request.args.get("q", "")
    if not query:
        return safe_json_response(data={"properties": []})

    try:
        # Get all properties for the vector service to filter/rank
        all_properties = database_service.get_properties()

        # Use vector service to find semantic matches
        # We'll mock a Customer object to satisfy the signature if needed
        class DummyCustomer:
            def __init__(self, query):
                self.preferences = query
                self.budget_min = 0
                self.budget_max = 1000000000
                self.preferred_bedrooms = 0
                self.preferred_bathrooms = 0
                self.preferred_type = ""
                self.location_preference = ""

        dummy = DummyCustomer(query)
        results = vector_service.search_properties(dummy, all_properties, top_k=20)

        formatted_results = []
        for res in results:
            p = res["property"]
            formatted_results.append({
                "id": p.id,
                "title": p.title,
                "address": p.address,
                "price": p.price,
                "property_type": p.property_type,
                "bedrooms": p.bedrooms,
                "bathrooms": p.bathrooms,
                "square_feet": p.square_feet,
                "score": res.get("score", 0),
                "image_filename": p.image_filename
            })

        return safe_json_response(data={"properties": formatted_results})
    except Exception as e:
        logging.error(f"Smart Search failed: {e}")
        return safe_json_response(message=f"Smart Search failed: {str(e)}", status=500)


@bp.route("/properties/extract-from-image", methods=["POST"])
def extract_property_from_image():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file:
        try:
            image_bytes = file.read()
            mime_type = file.mimetype or "image/jpeg"
            data = gemini_service.extract_property_from_image(image_bytes, mime_type)
            return jsonify(data)
        except Exception as e:
            logging.error(f"Image extraction error: {e}")
            return jsonify({"error": "Failed to extract data"}), 500

    return jsonify({"error": "Unknown error"}), 400


@bp.route("/properties/extract-from-text", methods=["POST"])
def extract_property_from_text():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        result = gemini_service.extract_property_from_text(text)
        # extract_property_from_text returns {entity, data: {...}, missing, confidence}
        # The frontend expects a flat dict of property fields (same as image endpoint)
        data = result.get("data", {}) if isinstance(result, dict) else {}
        return jsonify(data)
    except Exception as e:
        logging.error(f"Text extraction error: {e}")
        return jsonify({"error": "Failed to extract data"}), 500


@bp.route("/properties/<int:property_id>/ai-history", methods=["GET"])
def get_property_ai_history(property_id):
    """Get AI extraction history for a property"""
    history = database_service.get_ai_history(property_id)
    return jsonify([h.to_dict() for h in history])


@bp.route("/properties/ai-history/<int:history_id>", methods=["DELETE"])
def delete_property_ai_history(history_id):
    """Delete an AI extraction history record"""
    success = database_service.delete_ai_history(history_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"error": "Failed to delete history"}), 400