"""Deterministic mock extraction for staging/browser smoke (no network).

Enable with AI_FORM_ASSIST_MOCK=1 (and ENABLE_AI_FORM_ASSIST=1).
Parses simple English/Persian keywords from notes; never calls Gemini.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from services.ai_form_assist.schema_registry import get_form_schema
from services.ai_form_assist.types import ExtractionResult, RawFieldSuggestion, SourceType

# Persian digits → ASCII for mock heuristics
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _norm(text: str) -> str:
    return (text or "").translate(_PERSIAN_DIGITS)


def _source(
    image_parts: Optional[Sequence],
    audio_parts: Optional[Sequence],
) -> SourceType:
    has_i = bool(image_parts)
    has_a = bool(audio_parts)
    if has_i and has_a:
        return SourceType.mixed
    if has_i:
        return SourceType.image
    if has_a:
        return SourceType.audio
    return SourceType.text


def _add(
    out: List[RawFieldSuggestion],
    field: str,
    value,
    confidence: float,
    source: SourceType,
    rationale: str = "mock",
) -> None:
    if value is None or value == "":
        return
    out.append(
        RawFieldSuggestion(
            field=field,
            value=value,
            confidence=max(0.0, min(1.0, confidence)),
            source_type=source,
            rationale=rationale[:200],
        )
    )


def mock_extract(
    *,
    form: str,
    text: str = "",
    image_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
    audio_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
) -> ExtractionResult:
    schema = get_form_schema(form)
    source = _source(image_parts, audio_parts)
    raw = _norm(text)
    low = raw.lower()
    suggestions: List[RawFieldSuggestion] = []
    allowed = set(schema.fields.keys())

    def want(name: str) -> bool:
        return name in allowed

    # Shared budget / money — prefer explicit price/budget labels, else largest 5+ digit number
    money_val = None
    labeled = re.search(
        r"(?:\$|usd|price|قیمت|تومان|budget|offer)\s*[:=]?\s*([0-9]{4,}(?:[.,][0-9]{3})*)",
        low,
        re.I,
    )
    if labeled:
        try:
            money_val = int(re.sub(r"[^\d]", "", labeled.group(1)))
        except ValueError:
            money_val = None
    if money_val is None:
        nums = [int(re.sub(r"[^\d]", "", n)) for n in re.findall(r"\b[0-9]{5,}(?:[.,][0-9]{3})*\b", low)]
        if nums:
            money_val = max(nums)

    beds = re.search(r"(\d+)\s*(?:bed|br|bedroom|خواب|اتاق)", low)
    baths = re.search(r"(\d+)\s*(?:bath|bathroom|حمام)", low)
    area = re.search(r"(\d+)\s*(?:sqm|m2|sq\.?\s*ft|متر|متراژ)", low)

    if form == "property":
        title_m = re.search(r"(?:title|عنوان)[:\s]+([^\n,]{3,80})", raw, re.I)
        if want("title"):
            if title_m:
                _add(suggestions, "title", title_m.group(1).strip(), 0.92, source)
            elif raw.strip():
                first = raw.strip().split("\n")[0][:80]
                _add(suggestions, "title", first or "Mock listing", 0.91, source)
            else:
                _add(suggestions, "title", "Mock listing from media", 0.9, source)
        if want("bedrooms") and beds:
            _add(suggestions, "bedrooms", int(beds.group(1)), 0.93, source)
        if want("bathrooms") and baths:
            _add(suggestions, "bathrooms", int(baths.group(1)), 0.9, source)
        if want("square_feet") and area:
            _add(suggestions, "square_feet", int(area.group(1)), 0.88, source)
        if want("sale_price") and money_val and not re.search(r"rent|اجاره|rahn|رهن", low):
            _add(suggestions, "sale_price", money_val, 0.85, source)
        if want("listing_type"):
            if re.search(r"\b(rent|rental|اجاره)\b", low):
                _add(suggestions, "listing_type", "rental", 0.9, source)
            elif re.search(r"\b(sale|فروش|for sale)\b", low):
                _add(suggestions, "listing_type", "sale", 0.9, source)
        if want("address"):
            addr = re.search(r"(?:address|آدرس)[:\s]+([^\n]{5,120})", raw, re.I)
            if addr:
                _add(suggestions, "address", addr.group(1).strip(), 0.87, source)
        if want("neighborhood"):
            nb = re.search(r"(?:neighborhood|محله)[:\s]+([^\n,]{2,60})", raw, re.I)
            if nb:
                _add(suggestions, "neighborhood", nb.group(1).strip(), 0.86, source)
        if want("description") and len(raw.strip()) > 20:
            _add(suggestions, "description", raw.strip()[:2000], 0.8, source)
        if not suggestions and want("title"):
            _add(suggestions, "title", "Mock property", 0.9, source)

    elif form in ("customer", "recommendation"):
        name_m = re.search(r"(?:name|نام)[:\s]+([A-Za-z\u0600-\u06FF .'-]{2,60})", raw, re.I)
        if want("name") and name_m:
            _add(suggestions, "name", name_m.group(1).strip(), 0.9, source)
        if want("budget_max") and money_val:
            _add(suggestions, "budget_max", money_val, 0.88, source)
        if want("preferred_bedrooms") and beds:
            _add(suggestions, "preferred_bedrooms", int(beds.group(1)), 0.9, source)
        if want("preferred_bathrooms") and baths:
            _add(suggestions, "preferred_bathrooms", int(baths.group(1)), 0.88, source)
        loc = re.search(r"(?:location|محله|area)[:\s]+([^\n,]{2,60})", raw, re.I)
        if want("location_preference") and loc:
            _add(suggestions, "location_preference", loc.group(1).strip(), 0.86, source)
        if want("preferred_type"):
            for t in ("villa", "apartment", "condo", "house", "آپارتمان", "ویلا"):
                if t in low:
                    _add(suggestions, "preferred_type", t, 0.87, source)
                    break
        if want("customer_type"):
            if "investor" in low or "سرمایه" in low:
                _add(suggestions, "customer_type", "investor", 0.85, source)
            elif "seller" in low or "فروشنده" in low:
                _add(suggestions, "customer_type", "seller", 0.85, source)
            elif "buyer" in low or "خریدار" in low:
                _add(suggestions, "customer_type", "buyer", 0.85, source)
        if not suggestions and want("budget_max") and money_val:
            _add(suggestions, "budget_max", money_val, 0.85, source)
        if not suggestions and form == "customer" and want("name"):
            _add(suggestions, "name", "Mock Client", 0.9, source)

    elif form == "deal":
        if want("offer_amount") and money_val:
            _add(suggestions, "offer_amount", money_val, 0.9, source)
        if want("status"):
            for stage in ("prospecting", "qualified", "proposal", "negotiation", "closed"):
                if stage in low:
                    _add(suggestions, "status", stage, 0.88, source)
                    break
        if not suggestions and want("offer_amount"):
            _add(suggestions, "offer_amount", money_val or 500000, 0.85, source)

    elif form == "task":
        if want("title"):
            first = raw.strip().split("\n")[0][:120] if raw.strip() else "Mock task"
            _add(suggestions, "title", first, 0.92, source)
        if want("priority"):
            for p in ("urgent", "high", "medium", "low"):
                if p in low:
                    _add(suggestions, "priority", p, 0.9, source)
                    break
        if want("description") and len(raw.strip()) > 10:
            _add(suggestions, "description", raw.strip()[:2000], 0.8, source)
        date_m = re.search(r"(20\d{2}-\d{2}-\d{2})", raw)
        if want("due_date") and date_m:
            _add(suggestions, "due_date", date_m.group(1), 0.9, source)

    elif form == "agent":
        name_m = re.search(r"(?:name|نام)[:\s]+([A-Za-z\u0600-\u06FF .'-]{2,60})", raw, re.I)
        if want("name") and name_m:
            _add(suggestions, "name", name_m.group(1).strip(), 0.9, source)
        elif want("name") and raw.strip():
            _add(suggestions, "name", raw.strip().split("\n")[0][:60], 0.88, source)
        email_m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw)
        if want("email") and email_m:
            _add(suggestions, "email", email_m.group(0), 0.95, source)
        phone_m = re.search(r"(\+?\d[\d\s()-]{7,}\d)", raw)
        if want("phone") and phone_m:
            _add(suggestions, "phone", phone_m.group(1).strip(), 0.9, source)
        if want("specialization"):
            sp = re.search(r"(?:specialization|تخصص)[:\s]+([^\n,]{2,80})", raw, re.I)
            if sp:
                _add(suggestions, "specialization", sp.group(1).strip(), 0.88, source)
            elif "luxury" in low:
                _add(suggestions, "specialization", "Luxury residential", 0.85, source)
        if want("bio") and len(raw.strip()) > 15:
            _add(suggestions, "bio", raw.strip()[:2000], 0.8, source)

    # Media-only: ensure at least one high-confidence placeholder when schema allows
    if not suggestions and image_parts and want("title"):
        _add(suggestions, "title", "From image (mock)", 0.9, source)
    if not suggestions and audio_parts and want("title"):
        _add(suggestions, "title", "From audio (mock)", 0.9, source)
    if not suggestions and want("title"):
        _add(suggestions, "title", "Mock suggestion", 0.9, source)
    elif not suggestions and want("name"):
        _add(suggestions, "name", "Mock name", 0.9, source)

    return ExtractionResult(
        form=form,
        source_type=source,
        suggestions=suggestions,
        model_id="mock-extractor",
        degraded=False,
        error="",
    )
