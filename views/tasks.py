import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash

from database_service import database_service
from forms import TaskForm


bp = Blueprint("tasks", __name__)


@bp.route("/tasks")
def tasks():
    from flask import request

    agent_id = request.args.get("agent", type=int)
    status = request.args.get("status")
    tasks = database_service.get_tasks(agent_id=agent_id, status=status)
    agents = database_service.get_agents()
    return render_template("tasks.html", tasks=tasks, agents=agents, current_date=datetime.now())


@bp.route("/tasks/add", methods=["POST"])
def add_task():
    form = TaskForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("tasks"))
    try:
        due_date = None
        if form.due_date.data:
            try:
                due_date = datetime.strptime(form.due_date.data, "%Y-%m-%d")
            except Exception:
                pass
        database_service.add_task(
            form.title.data,
            form.description.data,
            int(form.agent_id.data),
            form.priority.data or "medium",
            "pending",
            due_date,
        )
        flash("Task added successfully!", "success")
    except Exception as e:
        logging.exception("Error adding task")
        flash(f"Error adding task: {str(e)}", "error")
    return redirect(url_for("tasks"))


@bp.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    try:
        task = database_service.complete_task(task_id)
        if task:
            flash("Task completed successfully!", "success")
        else:
            flash("Task not found!", "error")
    except Exception as e:
        logging.exception("Error completing task")
        flash(f"Error completing task: {str(e)}", "error")
    return redirect(url_for("tasks"))
