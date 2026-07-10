import logging
from typing import Any, Dict, List, Tuple

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database_service import database_service
from forms import DealForm
from utils.security_events import log_security_event

bp = Blueprint("deals", __name__)

# Canonical kanban columns (Stitch Deals Pipeline)
PIPELINE_STAGES: List[Tuple[str, str]] = [
    ("prospecting", "Prospecting"),
    ("contact_made", "Contact Made"),
    ("property_shown", "Property Shown"),
    ("offer_submitted", "Offer Submitted"),
    ("negotiation", "Negotiation"),
    ("closed_won", "Closed Won"),
]

# Legacy / free-text statuses → canonical column
STATUS_ALIASES = {
    "qualified": "prospecting",
    "lead": "prospecting",
    "new": "prospecting",
    "open": "prospecting",
    "active": "prospecting",
    "prospect": "prospecting",
    "contacted": "contact_made",
    "contact": "contact_made",
    "shown": "property_shown",
    "showing": "property_shown",
    "viewing": "property_shown",
    "offer": "offer_submitted",
    "offered": "offer_submitted",
    "submitted": "offer_submitted",
    "negotiating": "negotiation",
    "under_contract": "negotiation",
    "contract": "negotiation",
    "won": "closed_won",
    "closed": "closed_won",
    "sold": "closed_won",
    "lost": "closed_lost",
    "closed_lost": "closed_lost",
}


class SafeDict(dict):
    def __missing__(self, key):
        return {"count": 0, "value": 0}


def normalize_deal_status(raw: Any) -> str:
    """Map free-text / legacy deal status onto a pipeline column key."""
    s = (str(raw or "prospecting")).strip().lower().replace(" ", "_").replace("-", "_")
    if s in {k for k, _ in PIPELINE_STAGES}:
        return s
    if s in STATUS_ALIASES:
        return STATUS_ALIASES[s]
    # unknown → keep visible under prospecting rather than vanishing from board
    return "prospecting"


def group_deals_by_stage(deals: List[Any]) -> Dict[str, List[Any]]:
    buckets: Dict[str, List[Any]] = {key: [] for key, _ in PIPELINE_STAGES}
    buckets["closed_lost"] = []
    for d in deals or []:
        if getattr(d, "is_deleted", False):
            continue
        key = normalize_deal_status(getattr(d, "status", None))
        # attach normalized stage for templates / progress bars
        try:
            d.pipeline_stage = key
        except Exception:
            pass
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(d)
    return buckets


@bp.route("/deals")
def deals():
    deals_list = database_service.get_deals() or []
    properties = database_service.get_properties()
    customers = database_service.get_customers()
    agents = database_service.get_agents()

    stage_buckets = group_deals_by_stage(deals_list)

    pipeline_stats = SafeDict()
    for stage_key, _label in PIPELINE_STAGES:
        stage_deals = stage_buckets.get(stage_key) or []
        pipeline_stats[stage_key] = {
            "count": len(stage_deals),
            "value": sum(getattr(d, "offer_amount", 0) or 0 for d in stage_deals),
        }

    total_open = sum(
        pipeline_stats[k]["count"]
        for k, _ in PIPELINE_STAGES
        if k != "closed_won"
    )
    total_value = sum(
        pipeline_stats[k]["value"] for k, _ in PIPELINE_STAGES
    )

    highlight = request.args.get("highlight")
    return render_template(
        "deals.html",
        deals=deals_list,
        stage_buckets=stage_buckets,
        pipeline_stages=PIPELINE_STAGES,
        properties=properties,
        customers=customers,
        agents=agents,
        agents_list=agents,
        pipeline_stats=pipeline_stats,
        total_open_deals=total_open,
        total_pipeline_value=total_value,
        highlight=highlight,
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
        from datetime import UTC, datetime

        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
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
        log_security_event(
            "destructive_action",
            outcome="ok",
            action="delete_deal",
            resource_id=deal_id,
            user_id=session.get("user_id"),
        )
        flash("Deal deleted successfully!", "success")
    except Exception as e:
        logging.exception("Error deleting deal")
        flash(f"Error deleting deal: {str(e)}", "error")
    return redirect(url_for("deals"))
