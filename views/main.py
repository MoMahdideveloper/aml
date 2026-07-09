from flask import Blueprint, jsonify, render_template, redirect, flash, url_for

from database_service import database_service
from gemini_service import gemini_service

bp = Blueprint("main", __name__)


def _stat_value_and_trend(stats_dict, key, default=0):
    """Support plain ints from services and nested {value, trend} from legacy shapes."""
    raw = stats_dict.get(key, default)
    if isinstance(raw, dict):
        value = raw.get("value", default)
        trend = raw.get("trend") or {}
        return value if value is not None else default, trend
    return raw if raw is not None else default, {}


@bp.route("/")
@bp.route("/dashboard")
def dashboard():
    from datetime import datetime
    stats_dict = database_service.get_dashboard_stats()
    recent_properties = stats_dict.get("recent_properties") or []
    recent_deals = stats_dict.get("recent_deals") or []
    pending_tasks = database_service.get_tasks(status="pending")[:5]

    for deal in recent_deals:
        deal.property_name = deal.property.title if deal.property else "Unknown Property"
        deal.customer_name = deal.customer.name if deal.customer else "Unknown Customer"
        deal.agent_name = deal.agent.name if deal.agent else "Unknown Agent"

    for task in pending_tasks:
        setattr(task, "agent_name", task.agent.name if task.agent else "Unknown Agent")

    def _bento(label, icon, key):
        value, trend = _stat_value_and_trend(stats_dict, key)
        return {
            "label": label,
            "icon": icon,
            "value": value,
            "trend_direction": trend.get("direction", "up"),
            "trend_icon": trend.get("icon", "trending_up"),
            "trend_sign": trend.get("sign", "+"),
            "trend_percent": trend.get("percent", "0.0"),
        }

    bento_stats = [
        _bento("Total Properties", "domain", "total_properties"),
        _bento("Active Deals", "handshake", "active_deals"),
        _bento("Monthly Revenue", "account_balance", "total_deal_value"),
        _bento("Total Clients", "group", "total_customers"),
    ]

    recent_activities = []
    for prop in recent_properties[:3]:
        recent_activities.append({
            "icon": "add_home",
            "type": "New Property Listed",
            "time": prop.created_at.strftime("%b %d") if getattr(prop, "created_at", None) else "Recently",
            "description": f"Listed {prop.title} for ${prop.price:,.0f}" if getattr(prop, "price", 0) else f"Listed {prop.title}"
        })
    for deal in recent_deals[:3]:
        recent_activities.append({
            "icon": "handshake",
            "type": f"Deal {getattr(deal, 'status', 'Updated').title()}",
            "time": deal.created_at.strftime("%b %d") if getattr(deal, "created_at", None) else "Recently",
            "description": f"Offer ${getattr(deal, 'offer_amount', 0):,.0f} with {getattr(deal, 'customer_name', 'Client')}" if getattr(deal, "offer_amount", 0) else f"Deal with {getattr(deal, 'customer_name', 'Client')}"
        })
    if not recent_activities:
        recent_activities = [
            {
                "icon": "campaign",
                "type": "System Welcome",
                "time": "Just now",
                "description": "Welcome to your Real Estate CRM Dashboard.",
            }
        ]

    todays_schedule = [
        {"icon": "meeting_room", "title": "Client Private Viewing", "time": "10:30 AM - Penthouse Suite"},
        {"icon": "handshake", "title": "Contract Negotiation", "time": "2:00 PM - Modern Villa"},
        {"icon": "call", "title": "Follow-up Calls", "time": "4:30 PM - Prospective Buyers"}
    ]

    insights = {
        "quote": "Luxury property demand in prime metropolitan areas has risen by 14.2% over the last quarter.",
        "description": "High-net-worth investors are actively seeking turnkey properties with smart home integrations and sustainable architecture. Focus marketing efforts on properties exceeding $2M for optimal commission velocity."
    }

    return render_template(
        "dashboard.html",
        stats=bento_stats,
        recent_activities=recent_activities,
        currentMonth=datetime.now().strftime("%B %Y"),
        todays_schedule=todays_schedule,
        insights=insights,
        recent_properties=recent_properties,
        recent_deals=recent_deals,
        pending_tasks=pending_tasks,
    )


@bp.route("/recommendations")
def recommendations():
    customers = database_service.get_customers()
    return render_template("recommendations.html", customers=customers)


@bp.route("/get_customer_recommendations/<int:customer_id>")
def get_customer_recommendations(customer_id):
    """Get AI-powered property recommendations for a specific customer"""
    from database_service import database_service
    from gemini_service import gemini_service

    # Get the customer
    customer = database_service.get_customer(customer_id)
    if not customer:
        flash('Customer not found', 'error')
        return redirect(url_for('main.recommendations'))

    # Get all properties
    properties = database_service.get_properties()

    # Get recommendations using Gemini service
    recommendations_raw = gemini_service.get_property_recommendations(customer, properties)

    # Format recommendations for template
    recommendations = []
    for rec in recommendations_raw:
        property_obj = rec['property']
        recommendations.append({
            'property': property_obj,
            'match_score': int(rec.get('hybrid_score', 0) * 100),  # Convert 0-1 scale to 0-100
            'analysis': rec.get('analysis', 'AI analysis not available'),
            'reasons': rec.get('match_reasons', [])
        })

    return render_template(
        "recommendations.html",
        customers=[customer],  # Pass as list for template compatibility
        selected_customer=customer,
        recommendations=recommendations
    )


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
