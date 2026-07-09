"""
Default + filled outreach SMS templates for selected opportunities.

Placeholders:
  {name} {full_name} {phone} {need} {needs} {role} {title} {titles}
  {titles_scored} {list_block} {subtitle} {score} {scores}
  {reasons} {all_reasons} {count} {budget} {location} {type}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_OUTREACH_TEMPLATES: List[Dict[str, str]] = [
    {
        "id": "single_match",
        "label": "Single property intro",
        "body": (
            "Hi {name}, I found {title} as a {score}% match for your {need} need. "
            "{reasons}. Free this week for a quick call?"
        ),
    },
    {
        "id": "shortlist",
        "label": "Shortlist (multiple picks)",
        "body": (
            "Hi {name}, I shortlisted {count} options for your {need} need: {titles_scored}. "
            "Which should we view first?"
        ),
    },
    {
        "id": "shortlist_detail",
        "label": "Shortlist with details",
        "body": (
            "Hi {name}, for your {need} need I selected {count} matches:\n{list_block}\n"
            "Which ones interest you?"
        ),
    },
    {
        "id": "budget_fit",
        "label": "Budget-fit follow-up",
        "body": (
            "Hello {name}, based on your budget ({budget}) and preference for {type} "
            "in {location}, I have {titles_scored} ready to show. Reply YES for details."
        ),
    },
    {
        "id": "seller_comp",
        "label": "Seller / market update",
        "body": (
            "Hi {name}, market update for your {need} plan: {titles_scored}. "
            "Happy to walk you through comps when convenient."
        ),
    },
    {
        "id": "exchange",
        "label": "Exchange opportunity",
        "body": (
            "Hi {name}, regarding your home exchange ({need}): {titles_scored}. "
            "Shall I arrange a viewing?"
        ),
    },
    {
        "id": "soft_nudge",
        "label": "Soft nudge",
        "body": (
            "Hi {name}, just checking in — still interested in options around {location}? "
            "I can share {count} fresh match(es): {titles_scored}."
        ),
    },
]


def _join_reasons(reasons: Any, max_items: int = 2) -> str:
    if not reasons:
        return ""
    if isinstance(reasons, str):
        return reasons.strip()
    items = [str(r).strip() for r in reasons if r]
    return " · ".join(items[:max_items])


def _score_label(o: Dict[str, Any]) -> str:
    sc = o.get("score")
    if sc is None or str(sc).strip() == "":
        return ""
    try:
        return f"{int(round(float(sc)))}%"
    except (TypeError, ValueError):
        return f"{sc}%"


def _title_scored(o: Dict[str, Any]) -> str:
    title = str(o.get("title") or "listing").strip()
    sc = _score_label(o)
    return f"{title} ({sc})" if sc else title


def build_template_context(
    customer: Any,
    selected: List[Dict[str, Any]],
    phone: Optional[str] = None,
) -> Dict[str, str]:
    """Build placeholder map from customer + selected opportunity cards."""
    selected = [o for o in (selected or []) if isinstance(o, dict)]
    first = selected[0] if selected else {}
    titles = [str(o.get("title") or "").strip() for o in selected if o.get("title")]
    titles_scored = [_title_scored(o) for o in selected if o.get("title")]
    scores = []
    for o in selected:
        sc = _score_label(o)
        if sc:
            scores.append(sc)

    reasons_parts = []
    for o in selected[:5]:
        r = _join_reasons(o.get("reasons"))
        if r:
            reasons_parts.append(r)

    # Numbered list for multi-property SMS / detailed templates
    list_lines = []
    for i, o in enumerate(selected[:8], 1):
        sc = _score_label(o)
        sub = str(o.get("subtitle") or "").strip()
        line = f"{i}) {o.get('title') or 'Listing'}"
        if sc:
            line += f" · {sc}"
        if sub:
            line += f" · {sub[:40]}"
        list_lines.append(line)
    list_block = "\n".join(list_lines) if list_lines else "—"

    budget_min = first.get("budget_min")
    if budget_min in (None, "", 0):
        budget_min = getattr(customer, "budget_min", None) or 0
    budget_max = first.get("budget_max")
    if budget_max in (None, "", 0):
        budget_max = getattr(customer, "budget_max", None) or 0

    try:
        budget_min = int(float(budget_min or 0))
    except (TypeError, ValueError):
        budget_min = 0
    try:
        budget_max = int(float(budget_max or 0))
    except (TypeError, ValueError):
        budget_max = 0

    if first.get("budget_label"):
        budget = str(first.get("budget_label"))
    elif budget_min and budget_max:
        budget = f"${budget_min:,}–${budget_max:,}"
    elif budget_max:
        budget = f"up to ${budget_max:,}"
    elif budget_min:
        budget = f"from ${budget_min:,}"
    else:
        budget = "your range"

    needs = []
    for o in selected:
        n = str(o.get("brief_title") or o.get("need") or "").strip()
        if n and n not in needs:
            needs.append(n)
    if not needs:
        needs.append(str(getattr(customer, "customer_type", None) or "property"))

    need = " / ".join(needs[:3])
    role = first.get("kind") or getattr(customer, "customer_type", None) or "buyer"
    location = (
        first.get("location")
        or getattr(customer, "location_preference", None)
        or "your preferred area"
    )
    ptype = (
        first.get("preferred_type")
        or getattr(customer, "preferred_type", None)
        or "property"
    )

    return {
        "name": (getattr(customer, "name", None) or "there").split()[0],
        "full_name": getattr(customer, "name", None) or "there",
        "phone": phone or getattr(customer, "phone", None) or "",
        "need": need,
        "needs": ", ".join(needs),
        "role": str(role),
        "title": titles[0] if titles else "a listing",
        "titles": ", ".join(titles[:8]) if titles else "a few listings",
        "titles_scored": ", ".join(titles_scored[:8]) if titles_scored else "a few listings",
        "list_block": list_block,
        "subtitle": str(first.get("subtitle") or ""),
        "score": scores[0].rstrip("%") if scores else "—",
        "scores": ", ".join(s.rstrip("%") for s in scores) if scores else "—",
        "reasons": reasons_parts[0] if reasons_parts else "It lines up with your preferences.",
        "all_reasons": " | ".join(reasons_parts) if reasons_parts else "Good overall fit.",
        "count": str(len(selected) or 1),
        "budget": budget,
        "location": str(location or "your preferred area"),
        "type": str(ptype or "property"),
    }


def fill_template(body: str, ctx: Dict[str, str], collapse_whitespace: bool = False) -> str:
    out = body or ""
    # Longer keys first so {titles_scored} is not partially replaced by {titles}
    for key in sorted(ctx.keys(), key=len, reverse=True):
        out = out.replace("{" + key + "}", str(ctx[key] if ctx[key] is not None else ""))
    if collapse_whitespace:
        # Keep intentional newlines for multi-line shortlist_detail
        lines = [ln.strip() for ln in out.splitlines()]
        out = "\n".join(ln for ln in lines if ln != "" or True)
        # tidy double spaces on each line
        out = "\n".join(" ".join(ln.split()) for ln in out.splitlines())
    else:
        # Preserve newlines; only collapse runs of spaces/tabs on each line
        out = "\n".join(" ".join(ln.split()) for ln in out.splitlines()).strip()
    return out.strip()


def list_default_templates() -> List[Dict[str, str]]:
    return [dict(t) for t in DEFAULT_OUTREACH_TEMPLATES]


def pick_default_template_id(selected: List[Dict[str, Any]]) -> str:
    if not selected:
        return "soft_nudge"
    if len(selected) > 1:
        # Use detailed multi when many, shortlist when 2–3
        return "shortlist_detail" if len(selected) >= 3 else "shortlist"
    kind = (selected[0].get("kind") or "").lower()
    if kind == "seller":
        return "seller_comp"
    if kind == "exchange":
        return "exchange"
    return "single_match"


def adapt_template_for_selection(
    template_id: str,
    template_body: str,
    selected: List[Dict[str, Any]],
) -> tuple[str, str]:
    """
    If user picked a single-property template but selected multiple,
    upgrade to a multi-friendly template so all properties appear.
    """
    selected = selected or []
    if len(selected) <= 1:
        return template_id, template_body

    single_ish = {
        "single_match",
        "budget_fit",  # still uses titles_scored now — OK
    }
    # Old single_match body only had {title} — force multi templates
    if template_id == "single_match" or (
        template_body and "{titles" not in template_body and "{list_block}" not in template_body and "{count}" not in template_body
    ):
        tid = pick_default_template_id(selected)
        defaults = {t["id"]: t for t in DEFAULT_OUTREACH_TEMPLATES}
        return tid, defaults[tid]["body"]

    return template_id, template_body


def build_ai_prompt(customer: Any, selected: List[Dict[str, Any]], ctx: Dict[str, str]) -> str:
    lines = [
        "Write one SMS for a real-estate agent to send to a client.",
        "Keep it natural and professional.",
        f"If there are multiple properties ({ctx.get('count')}), mention ALL of them briefly with scores when available.",
        "Prefer under 400 characters; multi-line is OK for 3+ listings.",
        "Do not use markdown. Do not invent prices if not given.",
        f"Client name: {ctx.get('full_name') or ctx.get('name')}",
        f"Client phone: {ctx.get('phone') or 'n/a'}",
        f"Need / brief: {ctx.get('need')} (role: {ctx.get('role')})",
        f"Budget: {ctx.get('budget')}; location: {ctx.get('location')}; type: {ctx.get('type')}",
        f"Selected opportunities ({len(selected)}):",
    ]
    for i, o in enumerate(selected[:8], 1):
        score = o.get("score")
        score_s = f"{score}%" if score is not None else "n/a"
        reasons = _join_reasons(o.get("reasons"), 3)
        lines.append(
            f"{i}. [{o.get('kind') or 'match'} / need: {o.get('brief_title') or '—'}] "
            f"{o.get('title')} — {o.get('subtitle') or ''} "
            f"(score {score_s}). Reasons: {reasons or 'fit'}"
        )
    prefs = getattr(customer, "preferences", None) or ""
    if prefs:
        lines.append(f"Client notes: {str(prefs)[:240]}")
    lines.append("Return only the SMS text.")
    return "\n".join(lines)


def deterministic_ai_fallback(ctx: Dict[str, str], selected: List[Dict[str, Any]]) -> str:
    tid = pick_default_template_id(selected)
    body = next(
        (t["body"] for t in DEFAULT_OUTREACH_TEMPLATES if t["id"] == tid),
        DEFAULT_OUTREACH_TEMPLATES[0]["body"],
    )
    return fill_template(body, ctx)


def compose_message(
    customer: Any,
    selected: List[Dict[str, Any]],
    *,
    phone: Optional[str] = None,
    use_ai: bool = False,
    template_id: str = "",
    template_body: str = "",
    ai_generate_fn=None,
) -> Dict[str, Any]:
    """
    Single entry point used by the API.
    Returns {message, source, context, recommended_template_id}.
    """
    selected = [o for o in (selected or []) if isinstance(o, dict)][:12]
    ctx = build_template_context(customer, selected, phone=phone)
    recommended = pick_default_template_id(selected)
    defaults = {t["id"]: t for t in list_default_templates()}

    message = ""
    source = "custom"
    tid = (template_id or "").strip()
    tbody = (template_body or "").strip()

    if use_ai:
        source = "ai"
        if callable(ai_generate_fn):
            try:
                message = (ai_generate_fn(customer, selected, ctx) or "").strip()
            except Exception:
                message = ""
        if not message:
            message = deterministic_ai_fallback(ctx, selected)
            source = "ai_fallback"
    else:
        if tid and not tbody and tid in defaults:
            tbody = defaults[tid]["body"]
        if tid or tbody:
            tid, tbody = adapt_template_for_selection(tid, tbody, selected)
            if not tbody and tid in defaults:
                tbody = defaults[tid]["body"]
            message = fill_template(tbody, ctx)
            source = f"template:{tid or 'custom'}"
        else:
            tid = recommended
            message = fill_template(defaults[tid]["body"], ctx)
            source = f"template:{tid}"

    context = {
        "customer_id": getattr(customer, "id", None),
        "name": getattr(customer, "name", None),
        "phone": phone or getattr(customer, "phone", None) or "",
        "email": getattr(customer, "email", None) or "",
        "customer_type": getattr(customer, "customer_type", None) or "buyer",
        "budget_min": getattr(customer, "budget_min", None) or 0,
        "budget_max": getattr(customer, "budget_max", None) or 0,
        "preferred_type": getattr(customer, "preferred_type", None) or "",
        "location_preference": getattr(customer, "location_preference", None) or "",
        "preferences": (getattr(customer, "preferences", None) or "")[:400],
        "selected_count": len(selected),
        "needs": list(
            {
                str(o.get("brief_title") or o.get("kind") or "need")
                for o in selected
            }
        ),
        "selected_titles": [str(o.get("title") or "") for o in selected],
        "placeholders": ctx,
        "recommended_template_id": recommended,
    }

    return {
        "message": message,
        "source": source,
        "context": context,
        "recommended_template_id": recommended,
        "char_count": len(message or ""),
    }
