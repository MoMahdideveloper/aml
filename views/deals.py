import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for

from database_service import database_service
from forms import DealForm

bp = Blueprint("deals", __name__)


class SafeDict(dict):
    def __missing__(self, key):
        return {"count": 0, "value": 0}


@bp.route("/deals")
def deals():
    deals = database_service.get_deals()
    properties = database_service.get_properties()
    customers = database_service.get_customers()
    agents = database_service.get_agents()
    
    pipeline_stats = SafeDict()
    stages = ["prospecting", "contact_made", "property_shown", "offer_submitted", "negotiation", "closed_won", "closed_lost"]
    for stage in stages:
        stage_deals = [d for d in deals if getattr(d, 'status', '') == stage]
        pipeline_stats[stage] = {
            "count": len(stage_deals),
            "value": sum(getattr(d, 'offer_amount', 0) or 0 for d in stage_deals)
        }
        
    return render_template(
        "deals.html",
        deals=deals,
        properties=properties,
        customers=customers,
        agents=agents,
        agents_list=agents,
        pipeline_stats=pipeline_stats,
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


@bp.route("/api/deals/<int:deal_id>")
def get_deal_json(deal_id):
    from flask import jsonify

    deal = database_service.get_deal(deal_id)
    if not deal or getattr(deal, "is_deleted", False):
        return jsonify({"error": "Deal not found"}), 404
    data = deal.to_dict()
    data["property_title"] = deal.property.title if deal.property else None
    data["customer_name"] = deal.customer.name if deal.customer else None
    data["agent_name"] = deal.agent.name if deal.agent else None
    data["notes"] = deal.notes or ""
    return jsonify(data)


@bp.route("/deals/<int:deal_id>/note", methods=["POST"])
def add_deal_note(deal_id):
    deal = database_service.get_deal(deal_id)
    if not deal or getattr(deal, "is_deleted", False):
        flash("Deal not found.", "error")
        return redirect(url_for("deals"))

    note = (request.form.get("note") or "").strip()
    if not note:
        flash("Note cannot be empty.", "error")
        return redirect(url_for("deals"))

    try:
        from datetime import datetime

        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        existing = deal.notes or ""
        new_notes = (existing + "\n" if existing else "") + f"[{stamp}] {note}"
        database_service.update_deal(deal_id, notes=new_notes)
        flash("Note added to deal.", "success")
    except Exception as e:
        logging.exception("Error adding deal note")
        flash(f"Error adding note: {str(e)}", "error")
    return redirect(url_for("deals"))


@bp.route("/deals/<int:deal_id>/delete", methods=["POST"])
def delete_deal(deal_id):
    deal = database_service.get_deal(deal_id)
    if not deal or getattr(deal, "is_deleted", False):
        flash("Deal not found.", "error")
        return redirect(url_for("deals"))

    try:
        database_service.delete_deal(deal_id)
        flash("Deal deleted successfully!", "success")
    except Exception as e:
        logging.exception("Error deleting deal")
        flash(f"Error deleting deal: {str(e)}", "error")
    return redirect(url_for("deals"))
