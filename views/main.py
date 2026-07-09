import logging
import os
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

    # Background match feed for dashboard (always visible)
    latest_matches = []
    match_stats = {"total": 0, "high": 0}
    try:
        from sqlalchemy_models import PropertyMatch

        match_stats["total"] = PropertyMatch.query.filter(
            PropertyMatch.status != "dismissed"
        ).count()
        match_stats["high"] = PropertyMatch.query.filter(
            PropertyMatch.status != "dismissed",
            PropertyMatch.match_score >= 0.7,
        ).count()
        latest_matches = _load_global_matches(6)
    except Exception:
        logging.debug("dashboard matches skipped", exc_info=True)

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
        latest_matches=latest_matches,
        match_stats=match_stats,
    )


from utils.match_profile import customer_preference_profile as _customer_preference_profile


def _serialize_property_matches(rows, limit: int = 20) -> List[Dict[str, Any]]:
    """Human-readable match rows for Match Center / dashboard / APIs."""
    from database import db
    from sqlalchemy_models import Customer, Property

    out: List[Dict[str, Any]] = []
    for m in rows[:limit]:
        prop = db.session.get(Property, m.property_id)
        cust = db.session.get(Customer, m.customer_id)
        if prop is None or getattr(prop, "is_deleted", False):
            continue
        score_pct = int(round(float(m.match_score or 0) * 100))
        reasons = []
        try:
            import json

            raw = m.match_reasons
            if raw:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, list):
                    reasons = [str(x) for x in parsed if x and not str(x).startswith("Score mix:")][:3]
        except Exception:
            reasons = []
        try:
            recs_url = url_for(
                "main.get_customer_recommendations", customer_id=m.customer_id
            )
            property_url = url_for(
                "properties.property_detail", property_id=prop.id
            )
        except RuntimeError:
            # Outside request context (scripts / tests)
            recs_url = f"/get_customer_recommendations/{m.customer_id}"
            property_url = f"/properties/{prop.id}"
        out.append(
            {
                "id": m.id,
                "customer_id": m.customer_id,
                "customer_name": cust.name if cust else f"Client #{m.customer_id}",
                "property_id": m.property_id,
                "property_title": prop.title or f"Property #{prop.id}",
                "property_address": prop.address or prop.neighborhood or "",
                "property_type": prop.property_type or "",
                "property_price": prop.price,
                "match_score": score_pct,
                "status": m.status or "pending",
                "priority": m.priority or "normal",
                "reasons": reasons,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "recs_url": recs_url,
                "property_url": property_url,
            }
        )
    return out


def _load_global_matches(limit: int = 24) -> List[Dict[str, Any]]:
    from sqlalchemy_models import PropertyMatch

    rows = (
        PropertyMatch.query.filter(PropertyMatch.status != "dismissed")
        .order_by(PropertyMatch.match_score.desc(), PropertyMatch.created_at.desc())
        .limit(limit * 2)
        .all()
    )
    return _serialize_property_matches(rows, limit=limit)


@bp.route("/recommendations")
def recommendations():
    customers = database_service.get_customers()
    agents = database_service.get_agents()
    global_matches = []
    try:
        global_matches = _load_global_matches(24)
    except Exception:
        logging.debug("global matches load failed", exc_info=True)
    return render_template(
        "recommendations.html",
        customers=customers,
        agents=agents,
        selected_customer=None,
        preference_profile=None,
        recommendations=None,
        saved_matches=None,
        global_matches=global_matches,
    )


def _probe_redis() -> Dict[str, Any]:
    """Best-effort Redis reachability (Celery broker)."""
    url = (
        os.environ.get("REDIS_URL")
        or os.environ.get("CELERY_BROKER_URL")
        or "redis://localhost:6379/0"
    )
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=0.8, socket_timeout=0.8)
        client.ping()
        return {"ok": True, "url_host": url.split("@")[-1] if "@" in url else url.replace("redis://", "")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160], "url_host": url.split("@")[-1] if "@" in url else url}


@bp.route("/api/matching/status")
def matching_system_status():
    """
    Frontend observability for background matching.
    Does not require Celery — reads DB queue/job tables and probes Redis.
    """
    import json
    from datetime import datetime, timedelta

    from sqlalchemy_models import (
        AgentNotification,
        MatchingJobRun,
        PropertyMatch,
        RematchQueue,
    )
    from celery_app import _rematch_queue_interval_seconds

    now = datetime.utcnow()
    redis_info = _probe_redis()

    pending = RematchQueue.query.filter_by(status="pending").count()
    processing = RematchQueue.query.filter_by(status="processing").count()
    failed = RematchQueue.query.filter_by(status="failed").count()
    done_24h = RematchQueue.query.filter(
        RematchQueue.status == "done",
        RematchQueue.updated_at >= now - timedelta(hours=24),
    ).count()

    last_run = (
        MatchingJobRun.query.order_by(MatchingJobRun.started_at.desc()).first()
    )
    last_completed = (
        MatchingJobRun.query.filter(
            MatchingJobRun.status.in_(["completed", "skipped"]),
            MatchingJobRun.finished_at.isnot(None),
        )
        .order_by(MatchingJobRun.finished_at.desc())
        .first()
    )

    matches_total = PropertyMatch.query.filter(
        PropertyMatch.status != "dismissed"
    ).count()
    matches_24h = PropertyMatch.query.filter(
        PropertyMatch.created_at >= now - timedelta(hours=24),
        PropertyMatch.status != "dismissed",
    ).count()
    unread_alerts = AgentNotification.query.filter_by(
        status="unread", notification_type="property_match"
    ).count()

    last_run_dict = None
    if last_run:
        summary = {}
        if last_run.result_summary:
            try:
                summary = json.loads(last_run.result_summary)
            except Exception:
                summary = {"raw": (last_run.result_summary or "")[:200]}
        last_run_dict = {
            **last_run.to_dict(),
            "summary": summary,
            "age_seconds": int((now - last_run.started_at).total_seconds())
            if last_run.started_at
            else None,
        }

    last_completed_dict = None
    if last_completed:
        last_completed_dict = last_completed.to_dict()
        if last_completed.finished_at:
            last_completed_dict["age_seconds"] = int(
                (now - last_completed.finished_at).total_seconds()
            )

    # "Active" means recent completed work OR redis up with pending queue being drained.
    # Without Celery, redis may be up but jobs never run — surface that clearly.
    recent_ok = bool(
        last_completed
        and last_completed.finished_at
        and (now - last_completed.finished_at) < timedelta(minutes=20)
    )
    if last_run and last_run.status == "running" and last_run.started_at:
        recent_ok = recent_ok or (now - last_run.started_at) < timedelta(minutes=10)

    worker_hint = "unknown"
    if redis_info.get("ok") and recent_ok:
        worker_hint = "likely_active"
    elif redis_info.get("ok") and pending > 0 and not recent_ok:
        worker_hint = "redis_ok_but_queue_stuck"  # Celery worker/beat probably not running
    elif redis_info.get("ok") and not recent_ok:
        worker_hint = "redis_ok_idle"
    elif not redis_info.get("ok"):
        worker_hint = "redis_down"

    return jsonify(
        {
            "redis": redis_info,
            "worker_hint": worker_hint,
            "frontend_can_run_now": True,
            "schedule": {
                "rematch_queue_seconds": _rematch_queue_interval_seconds(),
                "full_matching_minutes": int(
                    os.environ.get("MATCHING_INTERVAL_MINUTES", "15")
                ),
            },
            "queue": {
                "pending": pending,
                "processing": processing,
                "failed": failed,
                "done_24h": done_24h,
            },
            "matches": {
                "active_total": matches_total,
                "created_24h": matches_24h,
            },
            "alerts_unread": unread_alerts,
            "last_run": last_run_dict,
            "last_completed": last_completed_dict,
            "active": recent_ok or worker_hint == "likely_active",
            "message": {
                "likely_active": "Background matching looks active (recent job + Redis up).",
                "redis_ok_but_queue_stuck": "Redis is up but the rematch queue is not draining — start Celery worker + beat, or click Run matching now.",
                "redis_ok_idle": "Redis is up; no recent matching job. Queue may be empty, or beat has not fired yet.",
                "redis_down": "Redis is not reachable. Always-on Celery matching is offline — use Run matching now, or start Redis + worker + beat.",
                "unknown": "Could not determine worker status.",
            }.get(worker_hint, ""),
        }
    )


@bp.route("/api/matching/run-now", methods=["POST"])
def matching_run_now():
    """
    Run rematch queue + optional full cycle in-process (no Celery required).
    Powers the frontend "Run matching now" control.
    """
    from background_matcher import background_matcher
    from services.scheduler_service import process_rematch_queue_job
    from sqlalchemy_models import PropertyMatch, RematchQueue

    body = request.get_json(silent=True) or {}
    mode = (body.get("mode") or request.form.get("mode") or "queue_and_sweep").strip()
    customer_id = body.get("customer_id") or request.form.get("customer_id")
    try:
        customer_id = int(customer_id) if customer_id not in (None, "") else None
    except (TypeError, ValueError):
        customer_id = None

    results = {"mode": mode, "queue": None, "cycle": None, "hint": None}
    pending_before = RematchQueue.query.filter_by(status="pending").count()

    try:
        # Drain pending rematch items first (batch-sized)
        process_rematch_queue_job()
        pending_after = RematchQueue.query.filter_by(status="pending").count()
        results["queue"] = {
            "status": "processed",
            "pending_before": pending_before,
            "pending_after": pending_after,
            "drained": max(0, pending_before - pending_after),
        }
    except Exception as exc:
        logging.exception("run-now queue drain failed")
        results["queue"] = {"status": "error", "error": str(exc)}

    if mode in ("queue_and_sweep", "sweep", "full"):
        try:
            import time

            # Unique key per click — avoid hourly idempotency making the button a no-op
            run_key = f"ui_run_now_{customer_id or 'all'}_{int(time.time())}"
            results["cycle"] = background_matcher.run_matching_cycle(
                customer_ids=[customer_id] if customer_id else None,
                trigger_source="ui_run_now",
                idempotency_key=run_key,
            )
        except Exception as exc:
            logging.exception("run-now matching cycle failed")
            results["cycle"] = {"status": "error", "error": str(exc)}

    cycle = results.get("cycle") or {}
    saved = int(cycle.get("matches_saved") or 0)
    found = int(cycle.get("matches_found") or 0)
    status = cycle.get("status")
    if status == "skipped":
        results["hint"] = "Matching was skipped (duplicate). Click Run matching now again."
    elif saved == 0 and found == 0:
        results["hint"] = (
            "No matches above the score threshold. Align client prefs with inventory "
            "(apartment vs Persian listing types), then try again or use Get recommendations."
        )
    elif found > 0 and saved == 0:
        results["hint"] = (
            f"Found {found} candidates; none newly written (may already exist). "
            "Open a client to view saved background matches."
        )
    else:
        results["hint"] = (
            f"Handled {saved} match(es) (found {found}). "
            "Open a client — see “Saved background matches”."
        )

    # Full feed for Match Center (names + scores) — global so results always show
    recent_q = PropertyMatch.query.filter(PropertyMatch.status != "dismissed").order_by(
        PropertyMatch.match_score.desc(), PropertyMatch.created_at.desc()
    )
    recent = recent_q.limit(24).all()
    results["recent_matches"] = _serialize_property_matches(recent, limit=24)
    results["matches_total"] = PropertyMatch.query.filter(
        PropertyMatch.status != "dismissed"
    ).count()

    return jsonify({"status": "ok", "results": results})


@bp.route("/api/matching/recent")
def matching_recent_feed():
    """Always-on Match Center feed (no client selection required)."""
    limit = min(int(request.args.get("limit", 24)), 50)
    customer_id = request.args.get("customer_id", type=int)
    from sqlalchemy_models import PropertyMatch

    q = PropertyMatch.query.filter(PropertyMatch.status != "dismissed")
    if customer_id:
        q = q.filter_by(customer_id=customer_id)
    rows = q.order_by(
        PropertyMatch.match_score.desc(), PropertyMatch.created_at.desc()
    ).limit(limit * 2).all()
    items = _serialize_property_matches(rows, limit=limit)
    return jsonify(
        {
            "count": len(items),
            "total": PropertyMatch.query.filter(PropertyMatch.status != "dismissed").count(),
            "matches": items,
        }
    )


@bp.route(
    "/api/customers/<int:customer_id>/matches/<int:property_id>/dismiss",
    methods=["POST"],
)
def dismiss_customer_match(customer_id, property_id):
    """Mark a property–customer match as dismissed (excluded from future ranking)."""
    from sqlalchemy_models import PropertyMatch
    from database import db

    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        return jsonify({"error": "Customer not found"}), 404

    match = (
        PropertyMatch.query.filter_by(
            customer_id=customer_id,
            property_id=property_id,
        ).first()
    )
    if match:
        match.status = "dismissed"
        db.session.commit()
    else:
        # Create a dismissed shell so hard prefilter excludes it next time
        match = PropertyMatch(
            property_id=property_id,
            customer_id=customer_id,
            match_score=0.0,
            confidence_level="low",
            priority="low",
            status="dismissed",
            match_reasons="[]",
        )
        db.session.add(match)
        db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "customer_id": customer_id,
            "property_id": property_id,
            "match_id": match.id,
        }
    )


def _parse_brief_form(form) -> Dict[str, Any]:
    from utils.customer_opportunities import normalize_brief_role

    def _int(name, default=0):
        try:
            return int(form.get(name) or default)
        except (TypeError, ValueError):
            return default

    def _float(name, default=0):
        try:
            return float(form.get(name) or default)
        except (TypeError, ValueError):
            return default

    rel = form.get("related_property_id")
    try:
        related_property_id = int(rel) if rel not in (None, "", "0") else None
    except (TypeError, ValueError):
        related_property_id = None

    return {
        "title": (form.get("title") or "Opportunity").strip()[:160],
        "role": normalize_brief_role(form.get("role")),
        "budget_min": _float("budget_min"),
        "budget_max": _float("budget_max"),
        "preferred_bedrooms": _int("preferred_bedrooms"),
        "preferred_bathrooms": _int("preferred_bathrooms"),
        "preferred_type": (form.get("preferred_type") or "").strip()[:50],
        "location_preference": (form.get("location_preference") or "").strip()[:255],
        "preferences": (form.get("preferences") or "").strip(),
        "exchange_notes": (form.get("exchange_notes") or "").strip(),
        "related_property_id": related_property_id,
        "is_active": form.get("is_active", "1") not in ("0", "false", "off"),
    }


@bp.route("/customers/<int:customer_id>/briefs", methods=["POST"])
def create_customer_brief(customer_id):
    """Add a new opportunity need for this client (buy / sell / exchange / invest)."""
    from database import db
    from sqlalchemy_models import CustomerOpportunityBrief
    from utils.customer_opportunities import normalize_brief_role

    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        flash("Customer not found", "error")
        return redirect(url_for("main.recommendations"))

    data = _parse_brief_form(request.form)
    if data["budget_min"] and data["budget_max"] and data["budget_min"] > data["budget_max"]:
        flash("Minimum budget cannot be greater than maximum.", "error")
        return redirect(url_for("main.get_customer_recommendations", customer_id=customer_id))

    count = CustomerOpportunityBrief.query.filter_by(customer_id=customer_id).count()
    brief = CustomerOpportunityBrief(
        customer_id=customer_id,
        title=data["title"] or f"{data['role'].title()} need",
        role=data["role"],
        budget_min=int(data["budget_min"] or 0),
        budget_max=int(data["budget_max"] or 0),
        preferred_bedrooms=data["preferred_bedrooms"],
        preferred_bathrooms=data["preferred_bathrooms"],
        preferred_type=data["preferred_type"],
        location_preference=data["location_preference"],
        preferences=data["preferences"],
        exchange_notes=data["exchange_notes"],
        related_property_id=data["related_property_id"],
        is_active=True,
        sort_order=count,
    )
    db.session.add(brief)
    db.session.commit()
    flash(f'Added opportunity “{brief.title}”.', "success")
    return redirect(
        url_for("main.get_customer_recommendations", customer_id=customer_id)
        + f"#brief-{brief.id}"
    )


@bp.route("/customers/<int:customer_id>/briefs/<int:brief_id>/edit", methods=["POST"])
def edit_customer_brief(customer_id, brief_id):
    from database import db
    from sqlalchemy_models import CustomerOpportunityBrief

    customer = database_service.get_customer(customer_id)
    brief = db.session.get(CustomerOpportunityBrief, brief_id)
    if (
        not customer
        or getattr(customer, "is_deleted", False)
        or not brief
        or brief.customer_id != customer_id
    ):
        flash("Opportunity not found", "error")
        return redirect(url_for("main.recommendations"))

    data = _parse_brief_form(request.form)
    if data["budget_min"] and data["budget_max"] and data["budget_min"] > data["budget_max"]:
        flash("Minimum budget cannot be greater than maximum.", "error")
        return redirect(url_for("main.get_customer_recommendations", customer_id=customer_id))

    brief.title = data["title"] or brief.title
    brief.role = data["role"]
    brief.budget_min = int(data["budget_min"] or 0)
    brief.budget_max = int(data["budget_max"] or 0)
    brief.preferred_bedrooms = data["preferred_bedrooms"]
    brief.preferred_bathrooms = data["preferred_bathrooms"]
    brief.preferred_type = data["preferred_type"]
    brief.location_preference = data["location_preference"]
    brief.preferences = data["preferences"]
    brief.exchange_notes = data["exchange_notes"]
    brief.related_property_id = data["related_property_id"]
    brief.is_active = data["is_active"]
    db.session.commit()
    flash(f'Updated “{brief.title}”.', "success")
    return redirect(
        url_for("main.get_customer_recommendations", customer_id=customer_id)
        + f"#brief-{brief.id}"
    )


@bp.route("/customers/<int:customer_id>/briefs/<int:brief_id>/delete", methods=["POST"])
def delete_customer_brief(customer_id, brief_id):
    from database import db
    from sqlalchemy_models import CustomerOpportunityBrief

    brief = db.session.get(CustomerOpportunityBrief, brief_id)
    if not brief or brief.customer_id != customer_id:
        flash("Opportunity not found", "error")
        return redirect(url_for("main.recommendations"))
    title = brief.title
    brief.is_active = False
    db.session.commit()
    flash(f'Archived “{title}”.', "success")
    return redirect(url_for("main.get_customer_recommendations", customer_id=customer_id))


@bp.route(
    "/customers/<int:customer_id>/match-preferences",
    methods=["POST"],
)
def update_match_preferences(customer_id):
    """Update client matching preferences from the recommendations page, then re-rank."""
    customer = database_service.get_customer(customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        flash("Customer not found", "error")
        return redirect(url_for("main.recommendations"))

    try:
        budget_min = float(request.form.get("budget_min") or 0)
        budget_max = float(request.form.get("budget_max") or 0)
        preferred_bedrooms = int(request.form.get("preferred_bedrooms") or 0)
        preferred_bathrooms = int(request.form.get("preferred_bathrooms") or 0)
        preferred_type = (request.form.get("preferred_type") or "").strip()
        location_preference = (request.form.get("location_preference") or "").strip()
        preferences = (request.form.get("preferences") or "").strip()
        status = (request.form.get("status") or customer.status or "active").strip()
        from utils.customer_opportunities import normalize_customer_type

        customer_type = normalize_customer_type(request.form.get("customer_type"))

        if budget_min > 0 and budget_max > 0 and budget_min > budget_max:
            flash("Minimum budget cannot be greater than maximum budget.", "error")
            return redirect(url_for("main.get_customer_recommendations", customer_id=customer_id))

        database_service.update_customer(
            customer_id,
            budget_min=budget_min,
            budget_max=budget_max,
            preferred_bedrooms=preferred_bedrooms,
            preferred_bathrooms=preferred_bathrooms,
            preferred_type=preferred_type,
            location_preference=location_preference,
            preferences=preferences,
            customer_type=customer_type,
            status=status if status in ("active", "prospect", "lead", "inactive") else customer.status,
        )
        flash("Client match preferences saved. Re-ranking properties…", "success")
    except Exception as exc:
        logging.exception("Failed to update match preferences for customer %s", customer_id)
        flash(f"Could not save preferences: {exc}", "error")

    return redirect(url_for("main.get_customer_recommendations", customer_id=customer_id))


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
    preference_profile = _customer_preference_profile(customer)

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

        reasons = rec.get("reasons") or rec.get("match_reasons") or rec.get("pros") or []
        if not isinstance(reasons, list):
            reasons = [str(reasons)] if reasons else []

        # Multi-parameter score mix for UI bars (0–100 each)
        breakdown = rec.get("score_breakdown") or rec.get("hybrid_breakdown") or {}
        if not isinstance(breakdown, dict):
            breakdown = {}
        # Normalize keys agents see on the card
        param_keys = (
            "semantic",
            "budget",
            "location",
            "type",
            "rooms",
            "amenities",
            "size",
        )
        score_mix = []
        for key in param_keys:
            raw = breakdown.get(key)
            if raw is None:
                continue
            try:
                val = float(raw)
            except (TypeError, ValueError):
                continue
            # semantic sometimes arrives 0–1 from older paths
            if key == "semantic" and val <= 1.0:
                val = val * 100.0
            val = max(0.0, min(100.0, val))
            score_mix.append(
                {
                    "key": key,
                    "label": {
                        "semantic": "Semantic",
                        "budget": "Budget",
                        "location": "Location",
                        "type": "Type",
                        "rooms": "Rooms",
                        "amenities": "Amenities",
                        "size": "Size",
                    }.get(key, key.title()),
                    "value": int(round(val)),
                }
            )

        # If engine didn't return breakdown, compute live so UI still shows mix
        if not score_mix:
            try:
                from services.vector_service import vector_service

                live = vector_service.score_breakdown(
                    customer, property_obj, float(match_score)
                )
                for key in param_keys:
                    if key not in live:
                        continue
                    score_mix.append(
                        {
                            "key": key,
                            "label": {
                                "semantic": "Semantic",
                                "budget": "Budget",
                                "location": "Location",
                                "type": "Type",
                                "rooms": "Rooms",
                                "amenities": "Amenities",
                                "size": "Size",
                            }.get(key, key.title()),
                            "value": int(round(float(live[key]))),
                        }
                    )
                if live.get("hybrid") is not None and match_score == 0:
                    match_score = max(0, min(100, int(round(float(live["hybrid"])))))
            except Exception:
                logging.debug("score_mix fallback skipped", exc_info=True)

        # Human reasons: drop internal "Score mix:" lines from chips (shown as bars)
        display_reasons = [
            r for r in reasons if r and not str(r).startswith("Score mix:")
        ][:5]

        recommendations.append(
            {
                "property": property_obj,
                "match_score": match_score,
                "analysis": rec.get("analysis") or "AI analysis not available",
                "reasons": display_reasons,
                "pros": rec.get("pros") or [],
                "cons": rec.get("cons") or [],
                "score_mix": score_mix,
            }
        )

    recommendations.sort(key=lambda item: item["match_score"], reverse=True)

    # Multiple opportunity briefs per client (buy / sell / exchange / invest)
    saved_matches = []
    global_matches = []
    customer_opportunities = None
    opportunity_sections = []
    try:
        from sqlalchemy_models import PropertyMatch
        from utils.customer_opportunities import build_customer_briefs_with_opportunities

        rows = (
            PropertyMatch.query.filter_by(customer_id=customer.id)
            .filter(PropertyMatch.status != "dismissed")
            .order_by(PropertyMatch.match_score.desc())
            .limit(12)
            .all()
        )
        saved_matches = _serialize_property_matches(rows, limit=12)
        customer_opportunities = build_customer_briefs_with_opportunities(
            customer, limit_per_brief=6
        )
        opportunity_sections = customer_opportunities.get("sections") or []
        global_matches = _load_global_matches(24)
    except Exception:
        logging.exception("opportunities load failed")

    # Properties for linking seller/exchange briefs
    linkable_properties = []
    try:
        from sqlalchemy_models import Property

        linkable_properties = (
            Property.query.filter_by(is_deleted=False)
            .order_by(Property.updated_at.desc())
            .limit(80)
            .all()
        )
    except Exception:
        pass

    return render_template(
        "recommendations.html",
        customers=customers,
        agents=agents,
        selected_customer=customer,
        preference_profile=preference_profile,
        recommendations=recommendations,
        saved_matches=saved_matches,
        customer_opportunities=customer_opportunities,
        opportunity_sections=opportunity_sections,
        linkable_properties=linkable_properties,
        global_matches=global_matches,
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


@bp.route("/api/opportunities/message-templates")
def api_opportunity_message_templates():
    """Default SMS templates + prior messages the agent can reuse."""
    from utils.outreach_templates import list_default_templates
    from services.sms_service import sms_service

    customer_id = request.args.get("customer_id", type=int)
    defaults = list_default_templates()

    prior: List[Dict[str, Any]] = []
    seen = set()

    # Prior SMS bodies (global recent, then same-phone if customer known)
    try:
        history = sms_service.get_history(limit=40) or []
        phone = None
        if customer_id:
            cust = database_service.get_customer(customer_id)
            phone = getattr(cust, "phone", None) if cust else None
        for msg in history:
            body = (getattr(msg, "message", None) or "").strip()
            if not body or body in seen or len(body) < 12:
                continue
            # Prefer same recipient when phone known
            if phone and getattr(msg, "recipient", None):
                rec = str(msg.recipient)
                # soft match digits
                if phone.replace(" ", "") not in rec and rec not in phone.replace(" ", ""):
                    # still allow as general prior below
                    pass
            seen.add(body)
            prior.append(
                {
                    "id": f"prior-sms-{getattr(msg, 'id', len(prior))}",
                    "label": f"Prior SMS · {(body[:42] + '…') if len(body) > 42 else body}",
                    "body": body,
                    "source": "sms_history",
                }
            )
            if len(prior) >= 12:
                break
    except Exception:
        logging.debug("prior SMS templates unavailable", exc_info=True)

    # Prior in-app outbound messages for this customer
    if customer_id:
        try:
            from sqlalchemy_models import ClientMessage

            rows = (
                ClientMessage.query.filter_by(customer_id=customer_id, direction="outbound")
                .order_by(ClientMessage.created_at.desc())
                .limit(20)
                .all()
            )
            for msg in rows:
                body = (msg.body or "").strip()
                if not body or body in seen:
                    continue
                seen.add(body)
                prior.append(
                    {
                        "id": f"prior-app-{msg.id}",
                        "label": f"Prior note · {(body[:42] + '…') if len(body) > 42 else body}",
                        "body": body,
                        "source": "client_message",
                    }
                )
                if len(prior) >= 20:
                    break
        except Exception:
            logging.debug("prior app messages unavailable", exc_info=True)

    return jsonify({"ok": True, "defaults": defaults, "prior": prior})


@bp.route("/api/opportunities/compose-message", methods=["POST"])
def api_opportunity_compose_message():
    """
    Build an outreach SMS for selected opportunities.
    body: {
      customer_id, phone?, template_id? | template_body?,
      use_ai?: bool, selected: [{id,title,subtitle,score,reasons,kind,brief_title,...}]
    }
    """
    from utils.outreach_templates import compose_message, build_ai_prompt

    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "customer_id required"}), 400

    customer = database_service.get_customer(customer_id)
    if not customer:
        return jsonify({"ok": False, "error": "Customer not found"}), 404

    selected = data.get("selected") or []
    if not isinstance(selected, list):
        selected = []
    clean_selected: List[Dict[str, Any]] = []
    for item in selected[:12]:
        if isinstance(item, dict) and (item.get("title") or item.get("id") or item.get("property_id")):
            clean_selected.append(item)

    if not clean_selected:
        return jsonify({"ok": False, "error": "Select at least one opportunity"}), 400

    phone = (data.get("phone") or getattr(customer, "phone", None) or "").strip()

    def _ai_generate(cust, sels, ctx):
        from services.gemini_service import gemini_service as gs
        from database import db
        from sqlalchemy_models import Property

        # Single property: use matchmaker pitch
        if len(sels) == 1 and sels[0].get("property_id"):
            try:
                prop = db.session.get(Property, int(sels[0]["property_id"]))
                if prop:
                    score = int(sels[0].get("score") or 0)
                    reasons = sels[0].get("reasons") or []
                    benefits = [{"benefit": r} for r in reasons[:2]] if reasons else None
                    return gs.generate_matchmaker_pitch(
                        cust, prop, score, score, score, smart_benefits=benefits
                    )
            except Exception as exc:
                logging.debug("single matchmaker pitch failed: %s", exc)

        # Multi (or fallback): prompt that lists ALL selections
        prompt = build_ai_prompt(cust, sels, ctx)
        if getattr(gs, "provider", None) and getattr(gs.provider, "is_available", False):
            return (gs.provider.generate_market_analysis(prompt) or "").strip()
        return ""

    try:
        result = compose_message(
            customer,
            clean_selected,
            phone=phone,
            use_ai=bool(data.get("use_ai")),
            template_id=(data.get("template_id") or "").strip(),
            template_body=(data.get("template_body") or "").strip(),
            ai_generate_fn=_ai_generate if data.get("use_ai") else None,
        )
    except Exception as exc:
        logging.exception("compose-message failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, **result})


@bp.route("/api/opportunities/send-sms", methods=["POST"])
def api_opportunity_send_sms():
    """Send / queue SMS for selected opportunities to the client phone."""
    import os
    from services.sms_service import sms_service
    from database import db

    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    try:
        customer_id = int(customer_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "customer_id required"}), 400

    customer = database_service.get_customer(customer_id)
    if not customer:
        return jsonify({"ok": False, "error": "Customer not found"}), 404

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Message body required"}), 400

    phone = (data.get("phone") or customer.phone or "").strip()
    if not phone:
        return jsonify({"ok": False, "error": "No phone number for this client"}), 400

    provider = (
        data.get("provider")
        or os.environ.get("SMS_PROVIDER")
        or "log"
    ).strip().lower()
    also_log = data.get("also_log_thread", True)
    selected = data.get("selected") or []

    try:
        queued = sms_service.queue_messages([phone], message, provider=provider)
        stats = {"processed": 0, "sent": 0, "failed": 0}
        try:
            stats = sms_service.process_queue(batch_size=min(5, len(queued)))
        except Exception:
            logging.debug("SMS process_queue deferred", exc_info=True)

        # Optional: log into client messaging thread for history / prior templates
        if also_log:
            try:
                from sqlalchemy_models import ClientMessage

                note = ClientMessage()
                note.customer_id = customer_id
                note.body = message
                note.direction = "outbound"
                note.channel = "sms"
                note.is_read = True
                # Attach short selection summary when present
                if isinstance(selected, list) and selected:
                    titles = [
                        str(s.get("title"))
                        for s in selected[:5]
                        if isinstance(s, dict) and s.get("title")
                    ]
                    if titles:
                        note.body = message  # keep SMS text pure; summary unused
                db.session.add(note)
                db.session.commit()
            except Exception:
                db.session.rollback()
                logging.debug("client message log skipped", exc_info=True)

        # Surface provider error text when send failed (e.g. missing Melipayamak config)
        last_error = None
        try:
            for q in queued:
                db.session.refresh(q)
                if getattr(q, "status", None) == "failed" and getattr(q, "error_message", None):
                    last_error = q.error_message
                    break
        except Exception:
            pass

        return jsonify(
            {
                "ok": True,
                "queued": len(queued),
                "phone": phone,
                "provider": provider,
                "stats": stats,
                "message": message,
                "error_detail": last_error,
            }
        )
    except Exception as exc:
        logging.exception("opportunity SMS send failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


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
