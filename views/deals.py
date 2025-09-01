import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for

from database_service import database_service
from forms import DealForm

bp = Blueprint("deals", __name__)


@bp.route("/deals")
def deals():
    deals = database_service.get_deals()
    properties = database_service.get_properties()
    customers = database_service.get_customers()
    agents = database_service.get_agents()
    return render_template(
        "deals.html", deals=deals, properties=properties, customers=customers, agents=agents
    )


@bp.route("/deals/add", methods=["POST"])
def add_deal():
    form = DealForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("deals"))
    try:
        database_service.add_deal(
            int(form.property_id.data),
            int(form.customer_id.data),
            int(form.agent_id.data),
            form.status.data or "prospecting",
            float(form.offer_amount.data or 0),
        )
        flash("Deal added successfully!", "success")
    except Exception as e:
        logging.exception("Error adding deal")
        flash(f"Error adding deal: {str(e)}", "error")
    return redirect(url_for("deals"))


@bp.route("/deals/<int:deal_id>/update", methods=["POST"])
def update_deal(deal_id):
    offer_amount = request.form.get("offer_amount")
    status = request.form.get("status")
    updates = {}
    if status:
        updates["status"] = status
    if offer_amount:
        try:
            updates["offer_amount"] = float(offer_amount)
        except ValueError:
            flash("Invalid offer amount format.", "error")
            return redirect(url_for("deals"))
    try:
        deal = database_service.update_deal(deal_id, **updates)
        if deal:
            flash("Deal updated successfully!", "success")
        else:
            flash("Deal not found!", "error")
    except Exception as e:
        logging.exception("Error updating deal")
        flash(f"Error updating deal: {str(e)}", "error")
    return redirect(url_for("deals"))
