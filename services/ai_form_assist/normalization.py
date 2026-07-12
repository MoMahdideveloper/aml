"""Persian-first normalization for AI form field values."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

# Persian / Arabic-Indic digits → ASCII
_DIGIT_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

_WS_RE = re.compile(r"\s+")
_PHONE_JUNK = re.compile(r"[^\d+]")
_MONEY_JUNK = re.compile(r"[^\d.]")


def normalize_digits(text: str) -> str:
    return (text or "").translate(_DIGIT_MAP)


def normalize_money(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = normalize_digits(str(value)).strip().lower()
    s = s.replace(",", "").replace("٬", "").replace("،", "")
    mult = 1.0
    if "میلیارد" in s or "billion" in s:
        mult = 1_000_000_000
    elif "میلیون" in s or "million" in s or re.search(r"(?<![a-z])m(?![a-z])", s):
        mult = 1_000_000
    elif "هزار" in s or re.search(r"(?<![a-z])k(?![a-z])", s) or re.search(r"\d\s*k\s*$", s):
        mult = 1_000
    # strip unit words
    s = re.sub(r"(تومان|ریال|rial|toman|irt|irr|میلیارد|میلیون|هزار|billion|million)", " ", s)
    s = _MONEY_JUNK.sub("", s.replace(" ", ""))
    if not s:
        return None
    try:
        return float(s) * mult
    except ValueError:
        return None


def normalize_area(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = normalize_digits(str(value)).lower()
    s = s.replace("متر مربع", " ").replace("مترمربع", " ").replace("sqm", " ")
    s = s.replace("sq ft", " ").replace("square feet", " ").replace("ft2", " ")
    m = re.search(r"([\d.]+)", s)
    if not m:
        return None
    try:
        return int(float(m.group(1)))
    except ValueError:
        return None


def normalize_phone(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    s = normalize_digits(str(value)).strip()
    s = _PHONE_JUNK.sub("", s)
    if s.startswith("0098"):
        s = "+98" + s[4:]
    elif s.startswith("98") and len(s) >= 12:
        s = "+" + s
    elif s.startswith("0") and len(s) == 11:
        s = "+98" + s[1:]
    if len(re.sub(r"\D", "", s)) < 8:
        return None
    return s


def normalize_date(value: Any, *, reference: Optional[date] = None) -> Optional[str]:
    """Return ISO YYYY-MM-DD or None. Relative dates require reference (else reject)."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = normalize_digits(str(value)).strip()
    # Explicit ISO
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return s
    # slash formats
    m = re.match(r"^(\d{4})[/.](\d{1,2})[/.](\d{1,2})$", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return None
    # Relative — only with reference
    rel = s.casefold()
    if rel in ("today", "امروز") and reference:
        return reference.isoformat()
    if rel in ("tomorrow", "فردا") and reference:
        from datetime import timedelta

        return (reference + timedelta(days=1)).isoformat()
    return None


def normalize_enum(value: Any, allowed: list[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    s = normalize_digits(str(value)).strip().casefold()
    allowed_l = {a.casefold(): a for a in allowed}
    if s in allowed_l:
        return allowed_l[s]
    # common aliases
    aliases = {
        "sale": "sale",
        "فروش": "sale",
        "rent": "rental",
        "rental": "rental",
        "اجاره": "rental",
        "buyer": "buyer",
        "خریدار": "buyer",
        "seller": "seller",
        "فروشنده": "seller",
    }
    mapped = aliases.get(s)
    if mapped and mapped.casefold() in allowed_l:
        return allowed_l[mapped.casefold()]
    return None


def normalize_field_value(field_type: str, value: Any, *, enum_values: list[str] | None = None) -> Any:
    """Dispatch normalization by registry field type."""
    ft = (field_type or "string").lower()
    if value is None or value == "":
        return None
    if ft == "number":
        return normalize_money(value)
    if ft == "integer":
        if "area" in str(value).lower() or "متر" in str(value):
            return normalize_area(value)
        money = normalize_money(value)
        if money is not None:
            return int(money)
        try:
            return int(float(normalize_digits(str(value))))
        except ValueError:
            return None
    if ft == "date":
        return normalize_date(value)
    if ft == "enum":
        return normalize_enum(value, enum_values or [])
    if ft == "id":
        try:
            return int(float(normalize_digits(str(value))))
        except ValueError:
            return None
    if ft in ("string", "text"):
        s = normalize_digits(str(value)).strip()
        s = _WS_RE.sub(" ", s)
        return s or None
    if ft == "boolean":
        s = str(value).strip().casefold()
        if s in ("1", "true", "yes", "بله", "آره"):
            return True
        if s in ("0", "false", "no", "خیر"):
            return False
        return None
    return value
