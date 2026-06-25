from flask import Blueprint, jsonify, render_template, send_file

from database_service import database_service
from gemini_service import gemini_service
import os
from utils.execution_tracer import log_execution

bp = Blueprint("main", __name__)



@bp.route('/')
@log_execution
def serve_code_html():
    """Serve the code.html file as the root page."""
    try:
        file_path = os.path.join(
            os.path.dirname(__file__),
            'stitch_kpi_performance_dashboard',
            'dashboard_overview',
            'code.html'
        )
        return send_file(file_path, mimetype='text/html')
    except FileNotFoundError:
        return "File not found: code.html", 404
    except Exception as e:
        # Log the error (optional)
        return f"Error reading file: {str(e)}", 500

@bp.route("/dashboard")
def dashboard():
    stats = database_service.get_dashboard_stats()
    recent_properties = stats["recent_properties"]
    recent_deals = stats["recent_deals"]
    pending_tasks = database_service.get_tasks(status="pending")[:5]

    for deal in recent_deals:
        deal.property_name = deal.property.title if deal.property else "Unknown Property"
        deal.customer_name = deal.customer.name if deal.customer else "Unknown Customer"
        deal.agent_name = deal.agent.name if deal.agent else "Unknown Agent"

    for task in pending_tasks:
        setattr(task, "agent_name", task.agent.name if task.agent else "Unknown Agent")

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_properties=recent_properties,
        recent_deals=recent_deals,
        pending_tasks=pending_tasks,
    )


@bp.route("/recommendations")
def recommendations():
    customers = database_service.get_customers()
    return render_template("recommendations.html", customers=customers)


@bp.route("/api/market-analysis")
def api_market_analysis():
    try:
        from datetime import datetime

        stats = database_service.get_dashboard_stats()
        properties = database_service.get_properties()
        result = gemini_service.generate_market_analysis(stats, properties)
        if isinstance(result, dict):
            result["updated_at"] = datetime.utcnow().isoformat() + "Z"
            return jsonify(result)
        return jsonify({"analysis": str(result), "bullets": [], "updated_at": datetime.utcnow().isoformat() + "Z"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

