import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from database import db
from database_service import database_service
from forms import PropertyForm
from sqlalchemy_models import Property

bp = Blueprint("properties", __name__)


@bp.route("/properties")
def properties():
    search_query = request.args.get("search", "")
    property_type = request.args.get("type", "")
    property_category = request.args.get("category", "")
    property_condition = request.args.get("condition", "")
    neighborhood = request.args.get("neighborhood", "")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    bedrooms = request.args.get("bedrooms", type=int)
    bathrooms = request.args.get("bathrooms", type=int)
    min_sqft = request.args.get("min_sqft", type=int)
    max_sqft = request.args.get("max_sqft", type=int)
    year_built_min = request.args.get("year_built_min", type=int)
    year_built_max = request.args.get("year_built_max", type=int)
    agent_id = request.args.get("agent_id", type=int)

    query = Property.query.options(selectinload(Property.agent))

    if search_query:
        like = f"%{search_query}%"
        query = query.filter(
            (Property.title.ilike(like))
            | (Property.address.ilike(like))
            | (Property.description.ilike(like))
        )
    if property_type:
        query = query.filter(Property.property_type == property_type)
    if property_category:
        query = query.filter(Property.property_category == property_category)
    if property_condition:
        query = query.filter(Property.property_condition == property_condition)
    if neighborhood:
        query = query.filter(Property.neighborhood == neighborhood)
    if min_price is not None:
        query = query.filter(Property.price >= min_price)
    if max_price is not None:
        query = query.filter(Property.price <= max_price)
    if bedrooms is not None:
        query = query.filter(Property.bedrooms >= bedrooms)
    if bathrooms is not None:
        query = query.filter(Property.bathrooms >= bathrooms)
    if min_sqft is not None:
        query = query.filter(Property.square_feet >= min_sqft)
    if max_sqft is not None:
        query = query.filter(Property.square_feet <= max_sqft)
    if year_built_min is not None:
        query = query.filter(Property.year_built >= year_built_min)
    if year_built_max is not None:
        query = query.filter(Property.year_built <= year_built_max)
    if agent_id is not None:
        query = query.filter(Property.agent_id == agent_id)

    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)
    pagination = query.order_by(Property.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    properties = pagination.items

    agents = database_service.get_agents()
    property_types = sorted(
        v[0] for v in db.session.query(func.distinct(Property.property_type)).all() if v[0]
    )
    neighborhoods = sorted(
        v[0] for v in db.session.query(func.distinct(Property.neighborhood)).all() if v[0]
    )
    property_conditions = ["excellent", "good", "fair", "needs_renovation"]
    property_categories = ["residential", "commercial", "industrial"]

    for prop in properties:
        setattr(prop, "agent_name", prop.agent.name if prop.agent else "Unassigned")

    return render_template(
        "properties.html",
        properties=properties,
        agents=agents,
        property_types=property_types,
        neighborhoods=neighborhoods,
        property_conditions=property_conditions,
        property_categories=property_categories,
        pagination=pagination,
        page=page,
        per_page=per_page,
        search_query=search_query,
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
    )


@bp.route("/properties/add", methods=["POST"])
def add_property():
    form = PropertyForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("properties"))

    try:
        listing_type = form.listing_type.data or "sale"
        if listing_type == "sale":
            price = float(form.sale_price.data or 0)
            rahn = None
            ejare = None
        else:
            price = 0
            rahn = float(form.rahn.data) if form.rahn.data not in (None, "") else None
            ejare = float(form.ejare.data) if form.ejare.data not in (None, "") else None

        database_service.add_property(
            form.title.data,
            form.address.data,
            price,
            form.property_type.data,
            int(form.bedrooms.data or 0),
            int(form.bathrooms.data or 0),
            int(form.square_feet.data or 0),
            form.description.data or "",
            "active",
            int(form.agent_id.data) if form.agent_id.data else None,
            int(form.year_built.data) if form.year_built.data else None,
            int(form.parking_spaces.data or 0),
            int(form.floors.data or 1),
            int(form.units.data or 1),
            form.property_condition.data or "good",
            "",
            "",
            None,
            form.property_features.data or "",
            form.neighborhood.data or "",
            form.property_category.data or "residential",
            listing_type,
            rahn,
            ejare,
        )
        flash(f'Property "{form.title.data}" added successfully!', "success")
    except Exception as e:
        logging.exception("Error adding property")
        flash(f"Error adding property: {str(e)}", "error")
    return redirect(url_for("properties"))
