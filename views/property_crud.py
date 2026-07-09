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


def _form_data(form, name, default=None):
    """Safe access for optional WTForms fields not present on every form class."""
    field = getattr(form, name, None)
    if field is None:
        return default
    return getattr(field, "data", default)


def _form_str(form, name, default=""):
    val = _form_data(form, name, default)
    if val is None:
        return default
    return str(val).strip()


def _form_int(form, name, default=None):
    val = _form_data(form, name, None)
    if val in (None, ""):
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _form_float(form, name, default=None):
    val = _form_data(form, name, None)
    if val in (None, ""):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


@bp.route("/properties/add", methods=["POST"])
def add_property():
    form = PropertyForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("properties.properties"))

    try:
        listing_type = _form_data(form, "listing_type") or "sale"
        if listing_type == "sale":
            price = int(_form_data(form, "sale_price") or 0)
            rahn = None
            ejare = None
        else:
            price = 0
            rahn = _form_int(form, "rahn")
            ejare = _form_int(form, "ejare")

        image_filename = None
        image_field = getattr(form, "image", None)
        if image_field is not None and image_field.data:
            file = image_field.data
            filename = secure_filename(file.filename or "")
            if filename:
                upload_folder = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                image_filename = filename

        property_obj = database_service.add_property(
            form.title.data,
            form.address.data,
            price,
            form.property_type.data,
            int(form.bedrooms.data or 0),
            int(form.bathrooms.data or 0),
            int(form.square_feet.data or 0),
            form.description.data or "",
            _form_str(form, "status", "active") or "active",
            int(form.agent_id.data) if form.agent_id.data else None,
            int(form.year_built.data) if form.year_built.data else None,
            int(form.parking_spaces.data or 0),
            int(form.floors.data or 1),
            int(form.units.data or 1),
            form.property_condition.data or "good",
            _form_str(form, "heating_type"),
            _form_str(form, "cooling_type"),
            None,
            form.property_features.data or "",
            form.neighborhood.data or "",
            form.property_category.data or "residential",
            listing_type,
            rahn,
            ejare,
            image_filename=image_filename,
            latitude=_form_data(form, "latitude"),
            longitude=_form_data(form, "longitude"),
            document_type=_form_str(form, "document_type") or None,
            floor_number=_form_int(form, "floor_number"),
            built_area=_form_int(form, "built_area"),
            land_area=_form_int(form, "land_area"),
            floor_covering=_form_str(form, "floor_covering") or None,
            facade_type=_form_str(form, "facade_type") or None,
            wall_covering=_form_str(form, "wall_covering") or None,
            cabinet_type=_form_str(form, "cabinet_type") or None,
            property_direction=_form_str(form, "property_direction") or None,
            is_exchangeable=bool(_form_data(form, "is_exchangeable") or False),
            boundary_width=_form_float(form, "boundary_width"),
            density=_form_str(form, "density") or None,
            commercial_status=_form_str(form, "commercial_status") or None,
            usage_type=_form_str(form, "usage_type") or None,
            ceiling_count=_form_int(form, "ceiling_count"),
            permit_ceiling=_form_str(form, "permit_ceiling") or None,
            property_length=_form_float(form, "property_length"),
            property_height=_form_float(form, "property_height"),
            price_per_meter=_form_int(form, "price_per_meter"),
            custom_fields=_form_str(form, "custom_fields"),
            is_ai_extracted=bool(_form_data(form, "is_ai_extracted") or False),
            ai_raw_data=_form_data(form, "ai_raw_data"),
            source=_form_str(form, "source", "manual") or "manual",
        )

        flash(f'Property "{form.title.data}" added successfully!', "success")

    except Exception as e:
        logging.exception("Error adding property")
        flash(f"Error adding property: {str(e)}", "error")
    return redirect(url_for("properties.properties"))


@bp.route("/properties/<int:property_id>", methods=["PUT", "POST"])
@handle_property_errors
@handle_database_connection_error
@validate_property_id
@require_property_exists
@validate_property_data(
    required_fields=['title', 'address', 'property_type'],
    optional_fields=['bedrooms', 'bathrooms', 'square_feet', 'description', 'year_built']
)
@log_property_operation("update_property")
def update_property(property_id, property_obj):
    """Update property data with comprehensive validation and error handling"""

    def _required_text(field_name):
        value = (request.form.get(field_name) or "").strip()
        if not value:
            raise PropertyValidationError(f"{field_name.replace('_', ' ').title()} is required")
        return value

    def _parse_optional_number(raw_value, field_label):
        normalized = _normalize_numeric_input(raw_value)
        if normalized in (None, ""):
            return None
        try:
            return float(normalized)
        except (ValueError, TypeError):
            raise PropertyValidationError(f"Invalid pricing data: {field_label} must be a valid number")

    def _parse_optional_int(raw_value, field_label, min_value=None, max_value=None):
        normalized = _normalize_numeric_input(raw_value)
        if normalized in (None, ""):
            return None
        try:
            value = int(normalized)
        except (ValueError, TypeError):
            raise PropertyValidationError(f"Invalid numeric data: {field_label} must be a valid number")
        if min_value is not None and value < min_value:
            raise PropertyValidationError(f"{field_label} must be at least {min_value}")
        if max_value is not None and value > max_value:
            raise PropertyValidationError(f"{field_label} must be at most {max_value}")
        return value

    def _parse_int_field(field_name, default=0, min_value=None, max_value=None):
        raw_value = _normalize_numeric_input(request.form.get(field_name))
        if raw_value in (None, ""):
            value = default
        else:
            try:
                value = int(raw_value)
            except (ValueError, TypeError):
                raise PropertyValidationError(
                    f"Invalid numeric data: {field_name.replace('_', ' ')} must be a valid number"
                )

        if min_value is not None and value < min_value:
            raise PropertyValidationError(
                f"{field_name.replace('_', ' ').title()} must be between {min_value} and {max_value}"
                if max_value is not None
                else f"{field_name.replace('_', ' ').title()} must be at least {min_value}"
            )
        if max_value is not None and value > max_value:
            raise PropertyValidationError(
                f"{field_name.replace('_', ' ').title()} must be between {min_value} and {max_value}"
            )
        return value

    # Parse form data
    title = _required_text("title")
    address = _required_text("address")
    property_type = _required_text("property_type")
    bedrooms = _parse_int_field("bedrooms", 0)
    bathrooms = _parse_int_field("bathrooms", 0)
    square_feet = _parse_int_field("square_feet", 0)
    description = (request.form.get("description") or "").strip()
    year_built = _parse_optional_int("year_built")
    parking_spaces = _parse_int_field("parking_spaces", 0)
    floors = _parse_int_field("floors", 1)
    units = _parse_int_field("units", 1)
    property_condition = (request.form.get("property_condition") or "good").strip() or "good"
    heating_type = (request.form.get("heating_type") or "").strip()
    cooling_type = (request.form.get("cooling_type") or "").strip()
    neighborhood = (request.form.get("neighborhood") or "").strip()
    property_category = (request.form.get("property_category") or "residential").strip() or "residential"
    listing_type = (request.form.get("listing_type") or "sale").strip()
    if listing_type not in ["sale", "rental"]:
        listing_type = "sale"
    property_features = (request.form.get("property_features") or "").strip()
    agent_id = _parse_optional_int("agent_id")
    document_type = (request.form.get("document_type") or "").strip() or None
    floor_number = _parse_optional_int("floor_number")
    built_area = _parse_optional_int("built_area")
    land_area = _parse_optional_int("land_area")
    floor_covering = (request.form.get("floor_covering") or "").strip() or None
    facade_type = (request.form.get("facade_type") or "").strip() or None
    wall_covering = (request.form.get("wall_covering") or "").strip() or None
    cabinet_type = (request.form.get("cabinet_type") or "").strip() or None
    property_direction = (request.form.get("property_direction") or "").strip() or None
    is_exchangeable = bool(request.form.get("is_exchangeable"))
    boundary_width = _parse_optional_number("boundary_width")
    density = (request.form.get("density") or "").strip() or None
    commercial_status = (request.form.get("commercial_status") or "").strip() or None
    usage_type = (request.form.get("usage_type") or "").strip() or None
    ceiling_count = _parse_optional_int("ceiling_count")
    permit_ceiling = (request.form.get("permit_ceiling") or "").strip() or None
    property_length = _parse_optional_number("property_length")
    property_height = _parse_optional_number("property_height")
    price_per_meter = _parse_optional_int("price_per_meter")
    latitude = _parse_optional_number("latitude")
    longitude = _parse_optional_number("longitude")
    custom_fields = (request.form.get("custom_fields") or "").strip()

    # Set pricing fields based on listing type
    if listing_type == "sale":
        price = _parse_optional_int("sale_price", 0) or 0
        rahn = None
        ejare = None
    else:
        price = 0
        rahn = _parse_optional_int("rahn")
        ejare = _parse_optional_int("ejare")

    try:
        updated_property = database_service.update_property(
            property_id,
            title=title,
            address=address,
            price=price,
            property_type=property_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            square_feet=square_feet,
            description=description,
            year_built=year_built,
            parking_spaces=parking_spaces,
            floors=floors,
            units=units,
            property_condition=property_condition,
            heating_type=heating_type,
            cooling_type=cooling_type,
            neighborhood=neighborhood,
            property_category=property_category,
            listing_type=listing_type,
            rahn=rahn,
            ejare=ejare,
            property_features=property_features,
            agent_id=agent_id,
            document_type=document_type,
            floor_number=floor_number,
            built_area=built_area,
            land_area=land_area,
            floor_covering=floor_covering,
            facade_type=facade_type,
            wall_covering=wall_covering,
            cabinet_type=cabinet_type,
            property_direction=property_direction,
            is_exchangeable=is_exchangeable,
            boundary_width=boundary_width,
            density=density,
            commercial_status=commercial_status,
            usage_type=usage_type,
            ceiling_count=ceiling_count,
            permit_ceiling=permit_ceiling,
            property_length=property_length,
            property_height=property_height,
            price_per_meter=price_per_meter,
            latitude=latitude,
            longitude=longitude,
            custom_fields=custom_fields,
        )
        if not updated_property:
            raise PropertyOperationError("Failed to update property - no changes made")
    except Exception as e:
        if isinstance(e, (PropertyValidationError, PropertyOperationError)):
            raise
        logging.error(f"Database error updating property {property_id}: {str(e)}")
        raise PropertyOperationError(f"Failed to update property: {str(e)}")

    image_file = request.files.get("image")
    if image_file and image_file.filename:
        try:
            filename = secure_filename(image_file.filename)
            upload_folder = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            image_file.save(os.path.join(upload_folder, filename))
            database_service.update_property(property_id, image_filename=filename)
        except Exception as e:
            logging.error(f"Error saving image for property {property_id}: {str(e)}")
            raise PropertyOperationError(f"Failed to upload image: {str(e)}")

    property_data = _serialize_property_for_json(updated_property)
    return safe_json_response(message="Property updated successfully", data={"property": property_data})


@bp.route("/properties/<int:property_id>/delete", methods=["POST"])
@handle_property_errors
@handle_database_connection_error
@validate_property_id
@require_property_exists
@log_property_operation("delete_property")
def delete_property(property_id, property_obj):
    """Delete a property with enhanced error handling"""
    try:
        success = database_service.delete_property(property_id)
        if not success:
            raise PropertyOperationError("Failed to delete property")

        flash(f'Property "{property_obj.title}" deleted successfully!', "success")
        return redirect(url_for("properties.properties"))
    except Exception as e:
        if isinstance(e, PropertyOperationError):
            raise
        logging.error(f"Error deleting property {property_id}: {str(e)}")
        flash(f"Error deleting property: {str(e)}", "error")
        return redirect(url_for("properties.properties"))