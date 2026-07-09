import logging
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for

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
    now = datetime.now()
    return render_template(
        "tasks.html",
        tasks=tasks,
        agents=agents,
        agents_list=agents,
        current_date=now,
        now=now,
    )


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
            for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
                try:
                    due_date = datetime.strptime(form.due_date.data, fmt)
                    break
                except ValueError:
                    continue
        database_service.add_task(
            form.title.data,
            form.description.data or "",
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


@bp.route("/api/tasks/<int:task_id>")
def get_task_json(task_id):
    from flask import jsonify

    task = database_service.get_task(task_id)
    if not task or getattr(task, "is_deleted", False):
        return jsonify({"error": "Task not found"}), 404
    data = task.to_dict()
    data["agent_name"] = task.agent.name if task.agent else None
    return jsonify(data)


@bp.route("/tasks/<int:task_id>/edit", methods=["POST"])
def edit_task(task_id):
    task = database_service.get_task(task_id)
    if not task or getattr(task, "is_deleted", False):
        flash("Task not found.", "error")
        return redirect(url_for("tasks"))

    form = TaskForm()
    if not form.validate_on_submit():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Invalid form data."
        flash(first_error, "error")
        return redirect(url_for("tasks"))

    try:
        due_date = None
        if form.due_date.data:
            for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
                try:
                    due_date = datetime.strptime(form.due_date.data, fmt)
                    break
                except ValueError:
                    continue
        database_service.update_task(
            task_id,
            title=form.title.data,
            description=form.description.data or "",
            agent_id=int(form.agent_id.data),
            priority=form.priority.data or "medium",
            due_date=due_date,
        )
        flash("Task updated successfully!", "success")
    except Exception as e:
        logging.exception("Error updating task")
        flash(f"Error updating task: {str(e)}", "error")
    return redirect(url_for("tasks"))


@bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    task = database_service.get_task(task_id)
    if not task or getattr(task, "is_deleted", False):
        flash("Task not found.", "error")
        return redirect(url_for("tasks"))

    try:
        database_service.delete_task(task_id)
        flash("Task deleted successfully!", "success")
    except Exception as e:
        logging.exception("Error deleting task")
        flash(f"Error deleting task: {str(e)}", "error")
    return redirect(url_for("tasks"))
