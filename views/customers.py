import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from database_service import database_service
from forms import CustomerForm
from utils.security_events import log_security_event

bp = Blueprint("customers", __name__)


@bp.route("/customers")
def customers():
    from utils.match_profile import customer_preference_profile

    search_query = (request.args.get("search") or request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    customer_type = (request.args.get("customer_type") or "").strip()
    highlight = request.args.get("highlight")

    customers = database_service.get_customers()
    # Apply allowlisted list filters (saved views + form)
    if search_query:
        sq = search_query.lower()
        customers = [
            c
            for c in customers
            if sq in (c.name or "").lower()
            or sq in (c.email or "").lower()
            or sq in (c.phone or "")
        ]
    if status:
        customers = [c for c in customers if (c.status or "") == status]
    if customer_type:
        customers = [
            c
            for c in customers
            if (getattr(c, "customer_type", None) or "") == customer_type
        ]

    for customer in customers:
        setattr(customer, "total_deals", len(customer.deals))
        setattr(
            customer,
            "active_deals",
            len([d for d in customer.deals if d.status not in ["closed_won", "closed_lost"]]),
        )
        setattr(customer, "match_profile", customer_preference_profile(customer))
    agents = database_service.get_agents()

    saved_views = []
    uid = session.get("user_id")
    if uid:
        try:
            from services.saved_views_service import saved_views_service

            saved_views = saved_views_service.list_for_user(uid, "customers")
        except Exception:
            logging.exception("saved views list failed")

    return render_template(
        "customers.html",
        customers=customers,
        agents=agents,
        agents_list=agents,
        search_query=search_query,
        status=status,
        customer_type=customer_type,
        saved_views=saved_views,
        highlight=highlight,
    )


@bp.route("/customers/<int:customer_id>")
def customer_360(customer_id: int):
    """Customer 360 — chronological activity timeline."""
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    from services.customer_timeline_service import TimelineError, customer_timeline_service

    try:
        customer = customer_timeline_service.get_customer_or_404(customer_id)
    except TimelineError:
        flash("Customer not found.", "error")
        return redirect(url_for("customers.customers"))

    itype = (request.args.get("type") or "").strip() or None
    cursor = request.args.get("cursor")
    page = customer_timeline_service.build_timeline(
        customer_id, interaction_type=itype, cursor=cursor, limit=25
    )
    deals = [d for d in (customer.deals or []) if not getattr(d, "is_deleted", False)]
    agents = database_service.get_agents()
    from flask import current_app

    related = None
    if current_app.config.get("ENABLE_DERIVED_EDGES"):
        try:
            from services.relationship_graph import neighbors as graph_neighbors

            related = graph_neighbors("customer", customer_id, depth=1, rebuild_if_empty=True)
        except Exception:
            related = {"neighbors": [], "error": True}

    match_explanations = []
    try:
        from services.match_explain import list_customer_matches

        match_explanations = list_customer_matches(customer_id, limit=8)
    except Exception:
        match_explanations = []

    return render_template(
        "customers/customer_360.html",
        customer=customer,
        timeline=page,
        deals=deals,
        agents=agents,
        filter_type=itype or "",
        config=current_app.config,
        related=related,
        match_explanations=match_explanations,
    )




@bp.route("/customers/<int:customer_id>/interactions", methods=["POST"])
def create_interaction(customer_id: int):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    from datetime import datetime

    from services.customer_timeline_service import TimelineError, customer_timeline_service

    try:
        occurred = request.form.get("occurred_at")
        follow = request.form.get("follow_up_at")
        occurred_at = datetime.fromisoformat(occurred) if occurred else None
        follow_up_at = datetime.fromisoformat(follow) if follow else None
        deal_id = request.form.get("related_deal_id")
        prop_id = request.form.get("related_property_id")
        agent_id = request.form.get("agent_id")
        create_task = request.form.get("create_follow_up") == "1"
        customer_timeline_service.create_interaction(
            customer_id=customer_id,
            interaction_type=request.form.get("interaction_type") or "note",
            subject=request.form.get("subject") or "",
            body=request.form.get("body") or "",
            outcome=request.form.get("outcome") or "",
            occurred_at=occurred_at,
            follow_up_at=follow_up_at,
            actor_user_id=session.get("user_id"),
            actor_label=session.get("user_name") or "user",
            related_deal_id=int(deal_id) if deal_id else None,
            related_property_id=int(prop_id) if prop_id else None,
            agent_id_for_task=int(agent_id) if agent_id else None,
            create_follow_up_task=create_task or bool(follow_up_at),
        )
        flash("Activity logged.", "success")
    except TimelineError as e:
        flash(e.message, "error")
    except (TypeError, ValueError) as e:
        flash("Invalid form data.", "error")
    return redirect(url_for("customers.customer_360", customer_id=customer_id))


@bp.route(
    "/customers/<int:customer_id>/interactions/<int:interaction_id>/edit",
    methods=["POST"],
)
def edit_interaction(customer_id: int, interaction_id: int):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    from services.customer_timeline_service import TimelineError, customer_timeline_service

    try:
        row = customer_timeline_service.update_interaction(
            interaction_id,
            actor_user_id=session.get("user_id"),
            actor_label=session.get("user_name") or "user",
            subject=request.form.get("subject"),
            body=request.form.get("body"),
            outcome=request.form.get("outcome"),
        )
        if row.customer_id != customer_id:
            flash("Interaction does not belong to this customer.", "error")
    except TimelineError as e:
        flash(e.message, "error")
    return redirect(url_for("customers.customer_360", customer_id=customer_id))


@bp.route(
    "/customers/<int:customer_id>/interactions/<int:interaction_id>/delete",
    methods=["POST"],
)
def delete_interaction(customer_id: int, interaction_id: int):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))
    from services.customer_timeline_service import TimelineError, customer_timeline_service

    try:
        # ownership check
        from sqlalchemy_models import CustomerInteraction
        from database import db

        row = db.session.get(CustomerInteraction, interaction_id)
        if not row or row.customer_id != customer_id:
            flash("Not found.", "error")
            return redirect(url_for("customers.customer_360", customer_id=customer_id))
        customer_timeline_service.delete_interaction(
            interaction_id,
            actor_user_id=session.get("user_id"),
            actor_label=session.get("user_name") or "user",
        )
        flash("Activity deleted.", "success")
    except TimelineError as e:
        flash(e.message, "error")
    return redirect(url_for("customers.customer_360", customer_id=customer_id))


@bp.route("/customers/add", methods=["POST"])
def add_customer():
    form = CustomerForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("customers"))
    try:
        from utils.customer_opportunities import normalize_customer_type

        customer = database_service.add_customer(
            form.name.data,
            form.email.data,
            form.phone.data,
            float(form.budget_min.data or 0),
            float(form.budget_max.data or 0),
            int(form.preferred_bedrooms.data or 0),
            int(form.preferred_bathrooms.data or 0),
            form.preferred_type.data or "",
            form.location_preference.data or "",
        )
        ctype = normalize_customer_type(
            form.customer_type.data if hasattr(form, "customer_type") else None
        )
        extra = {"customer_type": ctype}
        if form.preferences.data:
            extra["preferences"] = form.preferences.data or ""
        database_service.update_customer(customer.id, **extra)
        flash(f'Customer "{form.name.data}" added successfully!', "success")
    except Exception as e:
        logging.exception("Error adding customer")
        flash(f"Error adding customer: {str(e)}", "error")
    return redirect(url_for("customers"))


@bp.route("/api/customers/<int:customer_id>")
def get_customer_json(customer_id):
    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        return jsonify({"error": "Customer not found"}), 404
    from utils.match_profile import customer_preference_profile

    data = customer.to_dict()
    data["match_profile"] = customer_preference_profile(customer)
    data["preferred_bedrooms"] = customer.preferred_bedrooms
    data["preferred_bathrooms"] = customer.preferred_bathrooms
    data["preferences"] = customer.preferences or ""
    data["status"] = customer.status or "active"
    return jsonify(data)


@bp.route("/customers/<int:customer_id>/edit", methods=["POST"])
def edit_customer(customer_id):
    from flask import request

    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        flash("Customer not found.", "error")
        return redirect(url_for("customers"))

    form = CustomerForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("customers"))

    try:
        from sqlalchemy_models import Customer
        existing = Customer.query.filter(
            Customer.email == form.email.data, Customer.id != customer_id
        ).first()
        if existing:
            flash(f"Email {form.email.data} is already in use by another customer.", "error")
            return redirect(url_for("customers"))

        status = (request.form.get("status") or customer.status or "active").strip()
        if status not in ("active", "prospect", "lead", "inactive"):
            status = customer.status or "active"

        from utils.customer_opportunities import normalize_customer_type

        ctype = normalize_customer_type(
            form.customer_type.data if hasattr(form, "customer_type") else request.form.get("customer_type")
        )
        database_service.update_customer(
            customer_id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            budget_min=float(form.budget_min.data or 0),
            budget_max=float(form.budget_max.data or 0),
            preferred_bedrooms=int(form.preferred_bedrooms.data or 0),
            preferred_bathrooms=int(form.preferred_bathrooms.data or 0),
            preferred_type=form.preferred_type.data or "",
            location_preference=form.location_preference.data or "",
            preferences=form.preferences.data or "",
            customer_type=ctype,
            status=status,
        )
        flash(f'Customer "{form.name.data}" updated successfully!', "success")
    except Exception as e:
        logging.exception("Error updating customer")
        flash(f"Error updating customer: {str(e)}", "error")
    return redirect(url_for("customers"))


@bp.route("/customers/<int:customer_id>/delete", methods=["POST"])
def delete_customer(customer_id):
    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        flash("Customer not found.", "error")
        return redirect(url_for("customers"))

    active_deals = [d for d in customer.deals if d.status not in ["closed_won", "closed_lost"] and not getattr(d, "is_deleted", False)]
    if active_deals:
        flash(f"Cannot delete customer '{customer.name}' because they have active deals.", "error")
        return redirect(url_for("customers"))

    try:
        database_service.delete_customer(customer_id)
        log_security_event(
            "destructive_action",
            outcome="ok",
            action="delete_customer",
            resource_id=customer_id,
            user_id=session.get("user_id"),
        )
        flash(f"Customer '{customer.name}' deleted successfully!", "success")
    except Exception as e:
        logging.exception("Error deleting customer")
        flash(f"Error deleting customer: {str(e)}", "error")
    return redirect(url_for("customers"))
