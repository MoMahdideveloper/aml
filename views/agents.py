import logging
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, url_for, request, jsonify, abort

from database_service import database_service
from forms import AgentForm

bp = Blueprint("agents", __name__)


def _agent_performance(agent):
    """Compute dashboard metrics for a single agent."""
    properties = [p for p in (agent.properties or []) if not getattr(p, "is_deleted", False)]
    deals = [d for d in (agent.deals or []) if not getattr(d, "is_deleted", False)]
    tasks = [t for t in (agent.tasks or []) if not getattr(t, "is_deleted", False)]

    active_listings = [p for p in properties if (getattr(p, "status", "") or "").lower() == "active"]
    pending_deals = [
        d
        for d in deals
        if (getattr(d, "status", "") or "").lower() not in ("closed_won", "closed_lost", "closed")
    ]
    pending_tasks = [t for t in tasks if (getattr(t, "status", "") or "").lower() == "pending"]
    completed_tasks = [t for t in tasks if (getattr(t, "status", "") or "").lower() == "completed"]

    pipeline_value = 0.0
    for d in pending_deals:
        try:
            pipeline_value += float(getattr(d, "offer_amount", 0) or 0)
        except (TypeError, ValueError):
            pass

    month_ago = datetime.utcnow() - timedelta(days=30)
    deals_this_month = []
    for d in deals:
        created = getattr(d, "created_at", None) or getattr(d, "updated_at", None)
        if created and created >= month_ago:
            deals_this_month.append(d)

    # Sort recent items
    recent_properties = sorted(
        properties,
        key=lambda p: getattr(p, "updated_at", None) or getattr(p, "created_at", None) or datetime.min,
        reverse=True,
    )[:8]
    recent_deals = sorted(
        deals,
        key=lambda d: getattr(d, "updated_at", None) or getattr(d, "created_at", None) or datetime.min,
        reverse=True,
    )[:8]
    upcoming_tasks = sorted(
        pending_tasks,
        key=lambda t: getattr(t, "due_date", None) or datetime.max,
    )[:10]

    return {
        "active_listings_count": len(active_listings),
        "total_listings": len(properties),
        "total_deals": len(deals),
        "pending_deals_count": len(pending_deals),
        "pending_tasks_count": len(pending_tasks),
        "completed_tasks_count": len(completed_tasks),
        "pipeline_value": pipeline_value,
        "deals_this_month": len(deals_this_month),
        "recent_properties": recent_properties,
        "recent_deals": recent_deals,
        "upcoming_tasks": upcoming_tasks,
        "active_listings": active_listings[:12],
    }


@bp.route("/agents")
def agents():
    agents = database_service.get_agents() or []
    # Stable name sort for list UX
    try:
        agents = sorted(agents, key=lambda a: (getattr(a, "name", "") or "").lower())
    except Exception:
        pass
    for agent in agents:
        props = [p for p in (agent.properties or []) if not getattr(p, "is_deleted", False)]
        deals = [d for d in (agent.deals or []) if not getattr(d, "is_deleted", False)]
        tasks = [t for t in (agent.tasks or []) if not getattr(t, "is_deleted", False)]
        setattr(
            agent,
            "active_listings",
            len([p for p in props if (getattr(p, "status", "") or "").lower() == "active"]),
        )
        setattr(agent, "total_deals", len(deals))
        setattr(
            agent,
            "pending_deals",
            len(
                [
                    d
                    for d in deals
                    if (getattr(d, "status", "") or "").lower()
                    not in ("closed_won", "closed_lost", "closed")
                ]
            ),
        )
        setattr(
            agent,
            "pending_tasks",
            len([t for t in tasks if (getattr(t, "status", "") or "").lower() == "pending"]),
        )
        # Ensure bio always present for template
        if not hasattr(agent, "bio") or agent.bio is None:
            setattr(agent, "bio", "")
    return render_template("agents.html", agents=agents)


@bp.route("/agents/<int:agent_id>")
@bp.route("/agents/<int:agent_id>/dashboard")
def agent_dashboard(agent_id):
    """Per-agent performance dashboard (Stitch Agent Dashboard)."""
    agent = database_service.get_agent(agent_id)
    if not agent:
        flash("Agent not found.", "error")
        return redirect(url_for("agents.agents"))

    metrics = _agent_performance(agent)
    return render_template(
        "agent_dashboard.html",
        agent=agent,
        metrics=metrics,
    )


@bp.route("/agents/add", methods=["POST"])
def add_agent():
    form = AgentForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("agents"))
    try:
        database_service.add_agent(
            form.name.data,
            form.email.data,
            form.phone.data,
            form.specialization.data or "",
            form.bio.data or "",
        )
        flash(f'Agent "{form.name.data}" added successfully!', "success")
    except Exception as e:
        logging.exception("Error adding agent")
        flash(f"Error adding agent: {str(e)}", "error")
    return redirect(url_for("agents"))


@bp.route("/api/agents/<int:agent_id>")
def get_agent_json(agent_id):
    agent = database_service.get_agent(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(agent.to_dict())


@bp.route("/agents/<int:agent_id>/edit", methods=["POST"])
def edit_agent(agent_id):
    agent = database_service.get_agent(agent_id)
    if not agent:
        flash("Agent not found.", "error")
        return redirect(url_for("agents"))

    form = AgentForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("agents"))

    try:
        from sqlalchemy_models import Agent
        existing_agent = Agent.query.filter(Agent.email == form.email.data, Agent.id != agent_id).first()
        if existing_agent:
            flash(f"Email {form.email.data} is already in use by another agent.", "error")
            return redirect(url_for("agents"))

        database_service.update_agent(
            agent_id,
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            specialization=form.specialization.data or "",
            bio=form.bio.data or "",
        )
        flash(f'Agent "{form.name.data}" updated successfully!', "success")
    except Exception as e:
        logging.exception("Error updating agent")
        flash(f"Error updating agent: {str(e)}", "error")
    return redirect(url_for("agents"))


@bp.route("/agents/<int:agent_id>/delete", methods=["POST"])
def delete_agent(agent_id):
    agent = database_service.get_agent(agent_id)
    if not agent:
        flash("Agent not found.", "error")
        return redirect(url_for("agents"))

    if agent.deals:
        flash(f"Cannot delete agent '{agent.name}' because they have associated deals.", "error")
        return redirect(url_for("agents"))
    if agent.tasks:
        flash(f"Cannot delete agent '{agent.name}' because they have associated tasks.", "error")
        return redirect(url_for("agents"))

    try:
        database_service.delete_agent(agent_id)
        flash(f"Agent '{agent.name}' deleted successfully!", "success")
    except Exception as e:
        logging.exception("Error deleting agent")
        flash(f"Error deleting agent: {str(e)}", "error")
    return redirect(url_for("agents"))

