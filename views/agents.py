import logging

from flask import Blueprint, flash, redirect, render_template, url_for, request, jsonify, abort

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

