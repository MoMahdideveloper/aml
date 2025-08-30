import logging
from flask import Blueprint, render_template, redirect, url_for, flash

from database_service import database_service
from forms import AgentForm


bp = Blueprint("agents", __name__)


@bp.route("/agents")
def agents():
    agents = database_service.get_agents()
    for agent in agents:
        setattr(
            agent, "active_listings", len([p for p in agent.properties if p.status == "active"])
        )
        setattr(agent, "total_deals", len(agent.deals))
        setattr(agent, "pending_tasks", len([t for t in agent.tasks if t.status == "pending"]))
    return render_template("agents.html", agents=agents)


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
