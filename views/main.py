import logging
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, render_template, redirect, flash, url_for, request

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


def _safe_num(val, default=0.0) -> float:
    try:
        if val is None:
            return float(default)
        return float(val)
    except (TypeError, ValueError):
        return float(default)


def _compute_market_metrics(properties: List[Any], stats: Optional[Dict] = None) -> Dict[str, Any]:
    """Derive portfolio market metrics from live inventory (no hard-coded demos)."""
    props = [p for p in (properties or []) if not getattr(p, "is_deleted", False)]
    stats = stats or {}

    total = len(props)
    active = sum(1 for p in props if (getattr(p, "status", None) or "").lower() == "active")
    sold = sum(1 for p in props if (getattr(p, "status", None) or "").lower() in ("sold", "rented"))
    pending = sum(1 for p in props if (getattr(p, "status", None) or "").lower() == "pending")

    sale_prices = []
    prices_per_sqft = []
    for p in props:
        price = _safe_num(getattr(p, "price", None))
        if price > 0:
            sale_prices.append(price)
            sqft = _safe_num(getattr(p, "square_feet", None))
            if sqft > 0:
                prices_per_sqft.append(price / sqft)

    avg_price = statistics.mean(sale_prices) if sale_prices else _safe_num(stats.get("avg_property_price"))
    median_price = statistics.median(sale_prices) if sale_prices else avg_price
    avg_ppsqft = statistics.mean(prices_per_sqft) if prices_per_sqft else 0.0

    neighborhoods = Counter(
        (getattr(p, "neighborhood", None) or "Unspecified").strip() or "Unspecified" for p in props
    )
    types = Counter((getattr(p, "property_type", None) or "Other").strip() or "Other" for p in props)
    statuses = Counter((getattr(p, "status", None) or "unknown").lower() for p in props)
    listing_types = Counter((getattr(p, "listing_type", None) or "sale").lower() for p in props)

    top_neighborhoods = [
        {"name": name, "count": count, "share": round(100.0 * count / total, 1) if total else 0}
        for name, count in neighborhoods.most_common(8)
    ]
    type_breakdown = [
        {"name": name, "count": count, "share": round(100.0 * count / total, 1) if total else 0}
        for name, count in types.most_common(8)
    ]

    # Simple inventory health: active share as months-of-supply proxy
    active_share = (100.0 * active / total) if total else 0
    months_of_supply = round(max(0.5, min(12.0, (active / max(sold, 1)) * 1.5)), 1) if total else 0

    return {
        "total_properties": total,
        "active_properties": active,
        "sold_properties": sold,
        "pending_properties": pending,
        "avg_price": avg_price,
        "median_price": median_price,
        "avg_price_per_sqft": avg_ppsqft,
        "months_of_supply": months_of_supply,
        "active_share": round(active_share, 1),
        "top_neighborhoods": top_neighborhoods,
        "type_breakdown": type_breakdown,
        "status_breakdown": [{"name": k, "count": v} for k, v in statuses.most_common()],
        "listing_breakdown": [{"name": k, "count": v} for k, v in listing_types.most_common()],
        "priced_count": len(sale_prices),
    }


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
            "description": f"Listed {prop.title} for ${prop.price:,.0f}" if getattr(prop, "price", 0) else f"Listed {prop.title}",
            "href": url_for("properties.property_detail", property_id=prop.id) if getattr(prop, "id", None) else None,
        })
    for deal in recent_deals[:3]:
        deal_href = None
        prop_id = getattr(getattr(deal, "property", None), "id", None) or getattr(deal, "property_id", None)
        if prop_id:
            deal_href = url_for("properties.property_detail", property_id=prop_id)
        recent_activities.append({
            "icon": "handshake",
            "type": f"Deal {getattr(deal, 'status', 'Updated').title()}",
            "time": deal.created_at.strftime("%b %d") if getattr(deal, "created_at", None) else "Recently",
            "description": f"Offer ${getattr(deal, 'offer_amount', 0):,.0f} with {getattr(deal, 'customer_name', 'Client')}" if getattr(deal, "offer_amount", 0) else f"Deal with {getattr(deal, 'customer_name', 'Client')}",
            "href": deal_href,
        })
    if not recent_activities:
        recent_activities = [
            {
                "icon": "campaign",
                "type": "System Welcome",
                "time": "Just now",
                "description": "Welcome to Platinum Heritage. Add listings and deals to populate this feed.",
                "href": url_for("properties"),
            }
        ]

    bento_stats[0]["href"] = url_for("properties")
    bento_stats[1]["href"] = url_for("deals")
    bento_stats[2]["href"] = url_for("deals")
    bento_stats[3]["href"] = url_for("customers")

    # Dynamic schedule = pending tasks (no hard-coded demo appointments)
    todays_schedule = []
    for task in pending_tasks:
        due = getattr(task, "due_date", None)
        due_label = due.strftime("%b %d") if due is not None and hasattr(due, "strftime") else "No due date"
        todays_schedule.append(
            {
                "icon": "task_alt",
                "title": getattr(task, "title", None) or getattr(task, "description", None) or "Task",
                "time": f"{due_label} · {getattr(task, 'agent_name', 'Unassigned')}",
            }
        )

    total_props, _ = _stat_value_and_trend(stats_dict, "total_properties")
    active_deals, _ = _stat_value_and_trend(stats_dict, "active_deals")
    deal_value, _ = _stat_value_and_trend(stats_dict, "total_deal_value")
    total_customers, _ = _stat_value_and_trend(stats_dict, "total_customers")
    try:
        deal_value_f = float(deal_value or 0)
    except (TypeError, ValueError):
        deal_value_f = 0.0

    insights = {
        "quote": (
            f"Portfolio pulse: {int(total_props or 0)} listings, "
            f"{int(active_deals or 0)} active deals, "
            f"{int(total_customers or 0)} clients."
        ),
        "description": (
            f"Pipeline value tracked at ${deal_value_f:,.0f}. "
            f"{len(pending_tasks)} pending task(s) need attention. "
            "Use AI Match to pair clients with inventory."
        ),
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
    agents = database_service.get_agents()
    return render_template(
        "recommendations.html",
        customers=customers,
        agents=agents,
        selected_customer=None,
        recommendations=None,
    )


@bp.route("/get_customer_recommendations/<int:customer_id>")
def get_customer_recommendations(customer_id):
    """Get AI-powered property recommendations for a specific customer"""
    from database_service import database_service
    from gemini_service import gemini_service

    customer = database_service.get_customer(customer_id)
    if not customer:
        flash("Customer not found", "error")
        return redirect(url_for("main.recommendations"))

    customers = database_service.get_customers()
    agents = database_service.get_agents()
    properties = database_service.get_properties()

    error_message = None
    recommendations = []
    try:
        recommendations_raw = gemini_service.get_property_recommendations(customer, properties) or []
    except Exception as exc:
        logging.exception("Failed to generate recommendations for customer %s", customer_id)
        recommendations_raw = []
        error_message = f"Recommendation engine error: {exc}"

    for rec in recommendations_raw:
        property_obj = rec.get("property")
        if property_obj is None:
            continue

        # gemini_service already returns match_score on a 0–100 scale.
        # Prefer match_score; fall back to hybrid_score (0–100 or 0–1).
        raw_score = rec.get("match_score")
        if raw_score is None:
            hybrid = rec.get("hybrid_score", 0) or 0
            try:
                hybrid_f = float(hybrid)
            except (TypeError, ValueError):
                hybrid_f = 0.0
            raw_score = hybrid_f * 100 if hybrid_f <= 1.0 else hybrid_f
        try:
            match_score = int(round(float(raw_score)))
        except (TypeError, ValueError):
            match_score = 0
        match_score = max(0, min(100, match_score))

        reasons = rec.get("reasons") or rec.get("match_reasons") or []
        if not isinstance(reasons, list):
            reasons = [str(reasons)] if reasons else []

        recommendations.append(
            {
                "property": property_obj,
                "match_score": match_score,
                "analysis": rec.get("analysis") or "AI analysis not available",
                "reasons": reasons,
                "pros": rec.get("pros") or [],
                "cons": rec.get("cons") or [],
            }
        )

    recommendations.sort(key=lambda item: item["match_score"], reverse=True)

    return render_template(
        "recommendations.html",
        customers=customers,
        agents=agents,
        selected_customer=customer,
        recommendations=recommendations,
        error_message=error_message,
    )


@bp.route("/api/market-analysis")
def api_market_analysis():
    try:
        from datetime import datetime

        stats = database_service.get_dashboard_stats()
        properties = database_service.get_properties()
        metrics = _compute_market_metrics(properties, stats if isinstance(stats, dict) else {})
        result = gemini_service.generate_market_analysis(stats, properties)
        if isinstance(result, dict):
            result["updated_at"] = datetime.utcnow().isoformat() + "Z"
            result["metrics"] = metrics
            return jsonify(result)
        return jsonify(
            {
                "analysis": str(result),
                "bullets": [],
                "metrics": metrics,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/market")
@bp.route("/market-analysis")
def market_analysis():
    """Market Analysis dashboard — portfolio metrics + AI insight."""
    from datetime import datetime

    stats = database_service.get_dashboard_stats() or {}
    properties = database_service.get_properties() or []
    metrics = _compute_market_metrics(properties, stats if isinstance(stats, dict) else {})

    ai_analysis = None
    ai_bullets: List[str] = []
    try:
        result = gemini_service.generate_market_analysis(stats, properties)
        if isinstance(result, dict):
            ai_analysis = result.get("analysis")
            ai_bullets = result.get("bullets") or []
        elif result:
            ai_analysis = str(result)
    except Exception as e:
        logging.warning("Market analysis AI unavailable: %s", e)
        ai_analysis = None

    if not ai_analysis:
        ai_analysis = (
            f"Portfolio pulse: {metrics['total_properties']} listings "
            f"({metrics['active_properties']} active). "
            f"Median price ${metrics['median_price']:,.0f}."
        )
    if not ai_bullets:
        top = metrics["top_neighborhoods"][:3]
        top_str = ", ".join(f"{n['name']} ({n['count']})" for n in top) or "N/A"
        ai_bullets = [
            f"Listings: {metrics['total_properties']} total, {metrics['active_properties']} active",
            f"Median price: ${metrics['median_price']:,.0f}",
            f"Top areas: {top_str}",
        ]

    return render_template(
        "market_analysis.html",
        metrics=metrics,
        ai_analysis=ai_analysis,
        ai_bullets=ai_bullets,
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@bp.route("/compare")
def property_compare():
    """Side-by-side property comparison matrix (up to 4 listings)."""
    properties = database_service.get_properties() or []
    properties = [p for p in properties if not getattr(p, "is_deleted", False)]

    raw_ids = request.args.getlist("ids") or []
    if not raw_ids and request.args.get("ids"):
        raw_ids = str(request.args.get("ids")).split(",")
    selected_ids: List[int] = []
    for item in raw_ids:
        try:
            selected_ids.append(int(str(item).strip()))
        except (TypeError, ValueError):
            continue
    # de-dupe preserve order, cap at 4
    seen = set()
    ordered_ids = []
    for i in selected_ids:
        if i not in seen:
            seen.add(i)
            ordered_ids.append(i)
        if len(ordered_ids) >= 4:
            break

    by_id = {getattr(p, "id", None): p for p in properties}
    selected = [by_id[i] for i in ordered_ids if i in by_id]

    # Catalog for picker (lightweight list, newest first-ish)
    catalog = sorted(
        properties,
        key=lambda p: getattr(p, "updated_at", None) or getattr(p, "created_at", None) or 0,
        reverse=True,
    )[:200]

    return render_template(
        "property_compare.html",
        catalog=catalog,
        selected=selected,
        selected_ids=ordered_ids,
    )


@bp.route("/calculators")
@bp.route("/roi")
def roi_calculator():
    """Investment ROI calculator with optional property prefill."""
    prefill = {
        "price": 500000,
        "down": 20,
        "rate": 6.5,
        "rent": 3500,
        "title": None,
        "property_id": None,
    }
    property_id = request.args.get("property_id", type=int)
    if property_id:
        prop = database_service.get_property(property_id)
        if prop:
            price = _safe_num(getattr(prop, "price", None), 500000)
            prefill["price"] = int(price) if price else 500000
            prefill["title"] = getattr(prop, "title", None)
            prefill["property_id"] = property_id
            # Rough rent estimate: 0.5% of price / month when no ejare
            ejare = getattr(prop, "ejare", None)
            if ejare:
                prefill["rent"] = int(_safe_num(ejare))
            elif price:
                prefill["rent"] = max(500, int(price * 0.005))

    return render_template("roi_calculator.html", prefill=prefill)


def _ensure_client_messages_table():
    """Create client_messages if missing (dev / test DBs without full migrate)."""
    try:
        from database import db
        from sqlalchemy_models import ClientMessage

        ClientMessage.__table__.create(bind=db.engine, checkfirst=True)
    except Exception as exc:
        logging.warning("client_messages table ensure failed: %s", exc)


@bp.route("/messaging")
@bp.route("/messaging/<int:customer_id>")
def messaging(customer_id: Optional[int] = None):
    """Client messaging portal — in-app conversation log per customer."""
    from database import db
    from sqlalchemy_models import ClientMessage, Customer

    _ensure_client_messages_table()

    customers = database_service.get_customers() or []
    agents = database_service.get_agents() or []

    selected = None
    if customer_id:
        selected = database_service.get_customer(customer_id)
    elif customers:
        selected = customers[0]

    # Last message preview per customer
    last_by_customer: Dict[int, Any] = {}
    try:
        recent = (
            ClientMessage.query.order_by(ClientMessage.created_at.desc()).limit(500).all()
        )
        for msg in recent:
            if msg.customer_id not in last_by_customer:
                last_by_customer[msg.customer_id] = msg
    except Exception as exc:
        logging.warning("Could not load message previews: %s", exc)

    thread = []
    if selected:
        try:
            thread = (
                ClientMessage.query.filter_by(customer_id=selected.id)
                .order_by(ClientMessage.created_at.asc())
                .limit(200)
                .all()
            )
            # Mark inbound as read when viewing
            for msg in thread:
                if msg.direction == "inbound" and not msg.is_read:
                    msg.is_read = True
            db.session.commit()
        except Exception as exc:
            logging.warning("Could not load thread: %s", exc)
            db.session.rollback()

    return render_template(
        "messaging.html",
        customers=customers,
        agents=agents,
        selected_customer=selected,
        thread=thread,
        last_by_customer=last_by_customer,
    )


@bp.route("/messaging/<int:customer_id>/send", methods=["POST"])
def messaging_send(customer_id: int):
    """Post a message into the client thread (app channel)."""
    from database import db
    from sqlalchemy_models import ClientMessage

    _ensure_client_messages_table()

    customer = database_service.get_customer(customer_id)
    if not customer:
        flash("Customer not found", "error")
        return redirect(url_for("main.messaging"))

    body = (request.form.get("body") or "").strip()
    direction = (request.form.get("direction") or "outbound").strip().lower()
    if direction not in ("outbound", "inbound"):
        direction = "outbound"
    agent_id = request.form.get("agent_id", type=int)

    if not body:
        flash("Message cannot be empty.", "error")
        return redirect(url_for("main.messaging", customer_id=customer_id))

    try:
        msg = ClientMessage()
        msg.customer_id = customer_id
        msg.agent_id = agent_id
        msg.body = body
        msg.direction = direction
        msg.channel = "app"
        msg.is_read = direction == "outbound"
        db.session.add(msg)
        db.session.commit()
        flash("Message saved.", "success")
    except Exception as exc:
        db.session.rollback()
        logging.exception("messaging_send failed")
        flash(f"Could not save message: {exc}", "error")

    return redirect(url_for("main.messaging", customer_id=customer_id))


@bp.route("/sms")
@bp.route("/sms-broadcast")
def sms_broadcast():
    """VIP SMS broadcast panel — queues outbound SMS via sms_service."""
    from services.sms_service import sms_service

    customers = database_service.get_customers() or []
    history = []
    try:
        history = sms_service.get_history(limit=40)
    except Exception as exc:
        logging.warning("SMS history unavailable: %s", exc)

    # Segment counts for UI
    vip = [c for c in customers if (getattr(c, "budget_max", 0) or 0) >= 1_000_000]
    buyers = [
        c
        for c in customers
        if (getattr(c, "preferred_type", "") or getattr(c, "status", "") or "").lower()
        in ("buyer", "active", "lead", "")
    ]
    with_phone = [c for c in customers if getattr(c, "phone", None)]

    segments = [
        {"id": "all", "label": f"All clients with phone ({len(with_phone)})", "count": len(with_phone)},
        {"id": "vip", "label": f"High budget ≥ $1M ({len(vip)})", "count": len(vip)},
        {"id": "buyers", "label": f"Active / buyer leads ({len(buyers)})", "count": len(buyers)},
    ]

    return render_template(
        "sms_broadcast.html",
        customers=customers,
        segments=segments,
        history=history,
        with_phone_count=len(with_phone),
    )


@bp.route("/sms/send", methods=["POST"])
def sms_send():
    """Queue SMS broadcast to a segment or explicit phones."""
    from services.sms_service import sms_service
    import os

    message = (request.form.get("message") or "").strip()
    segment = (request.form.get("segment") or "all").strip().lower()
    provider = (request.form.get("provider") or os.environ.get("SMS_PROVIDER") or "log").strip().lower()

    if not message:
        flash("Enter a message body.", "error")
        return redirect(url_for("main.sms_broadcast"))

    customers = database_service.get_customers() or []
    if segment == "vip":
        pool = [c for c in customers if (getattr(c, "budget_max", 0) or 0) >= 1_000_000]
    elif segment == "buyers":
        pool = customers
    else:
        pool = customers

    recipients = [getattr(c, "phone", None) for c in pool if getattr(c, "phone", None)]
    # Allow manual override phones
    manual = (request.form.get("manual_phones") or "").strip()
    if manual:
        for part in re_split_phones(manual):
            recipients.append(part)

    if not recipients:
        flash("No recipients with phone numbers in this segment.", "error")
        return redirect(url_for("main.sms_broadcast"))

    try:
        queued = sms_service.queue_messages(recipients, message, provider=provider)
        # Attempt immediate process with log provider so UI shows progress without Celery
        try:
            stats = sms_service.process_queue(batch_size=min(50, len(queued)))
            flash(
                f"Queued {len(queued)} SMS · processed {stats.get('processed', 0)} "
                f"(sent {stats.get('sent', 0)}, failed {stats.get('failed', 0)}).",
                "success",
            )
        except Exception:
            flash(f"Queued {len(queued)} SMS for delivery.", "success")
    except Exception as exc:
        logging.exception("sms_send failed")
        flash(f"SMS queue failed: {exc}", "error")

    return redirect(url_for("main.sms_broadcast"))


def re_split_phones(raw: str) -> List[str]:
    parts = []
    for chunk in raw.replace(";", ",").replace("\n", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts


@bp.route("/contracts")
@bp.route("/smart-contract")
def smart_contract():
    """Smart contract / lease draft generator from CRM parties."""
    from datetime import datetime

    properties = database_service.get_properties() or []
    properties = [p for p in properties if not getattr(p, "is_deleted", False)][:300]
    customers = database_service.get_customers() or []

    selected_property = None
    selected_customer = None
    pid = request.args.get("property_id", type=int)
    cid = request.args.get("customer_id", type=int)
    if pid:
        selected_property = database_service.get_property(pid)
    if cid:
        selected_customer = database_service.get_customer(cid)

    return render_template(
        "smart_contract.html",
        properties=properties,
        customers=customers,
        selected_property=selected_property,
        selected_customer=selected_customer,
        generated_on=datetime.now().strftime("%Y-%m-%d"),
    )


def _ensure_open_house_table():
    try:
        from database import db
        from sqlalchemy_models import OpenHouseCheckin

        OpenHouseCheckin.__table__.create(bind=db.engine, checkfirst=True)
    except Exception as exc:
        logging.warning("open_house_checkins ensure failed: %s", exc)


@bp.route("/kiosk")
@bp.route("/open-house")
def open_house_kiosk():
    """Open house kiosk — pick a property or show check-in form."""
    properties = database_service.get_properties() or []
    properties = [
        p
        for p in properties
        if not getattr(p, "is_deleted", False)
        and (getattr(p, "status", "") or "").lower() in ("active", "pending", "")
    ][:200]

    property_id = request.args.get("property_id", type=int)
    prop = database_service.get_property(property_id) if property_id else None

    return render_template(
        "open_house_kiosk.html",
        properties=properties,
        property=prop,
    )


@bp.route("/kiosk/<int:property_id>")
def open_house_kiosk_property(property_id: int):
    prop = database_service.get_property(property_id)
    if not prop:
        flash("Property not found", "error")
        return redirect(url_for("main.open_house_kiosk"))
    properties = database_service.get_properties() or []
    return render_template(
        "open_house_kiosk.html",
        properties=properties,
        property=prop,
    )


@bp.route("/kiosk/<int:property_id>/checkin", methods=["POST"])
def open_house_checkin(property_id: int):
    """Save open-house guest; upsert as customer lead when email is new."""
    from database import db
    from sqlalchemy_models import Customer, OpenHouseCheckin

    _ensure_open_house_table()

    prop = database_service.get_property(property_id)
    if not prop:
        flash("Property not found", "error")
        return redirect(url_for("main.open_house_kiosk"))

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    status_tags = (request.form.get("status_tags") or "").strip()

    if not name or not email or not phone:
        flash("Name, email, and phone are required.", "error")
        return redirect(url_for("main.open_house_kiosk_property", property_id=property_id))

    customer_id = None
    try:
        existing = Customer.query.filter(
            Customer.email == email,
            Customer.is_deleted.is_(False),
        ).first()
        if existing:
            customer_id = existing.id
            if phone and not existing.phone:
                existing.phone = phone
        else:
            customer = database_service.add_customer(
                name,
                email,
                phone,
                budget_min=0,
                budget_max=0,
                preferred_bedrooms=0,
                preferred_bathrooms=0,
                preferred_type="",
                location_preference=getattr(prop, "neighborhood", "") or "",
            )
            try:
                customer.status = "lead"
                db.session.commit()
            except Exception:
                db.session.rollback()
            customer_id = customer.id

        checkin = OpenHouseCheckin()
        checkin.property_id = property_id
        checkin.name = name
        checkin.email = email
        checkin.phone = phone
        checkin.status_tags = status_tags[:255]
        checkin.customer_id = customer_id
        db.session.add(checkin)
        db.session.commit()
        flash(f"Welcome, {name}! You’re checked in. An agent will follow up.", "success")
    except Exception as exc:
        db.session.rollback()
        logging.exception("open_house_checkin failed")
        flash(f"Check-in failed: {exc}", "error")

    return redirect(url_for("main.open_house_kiosk_property", property_id=property_id))
