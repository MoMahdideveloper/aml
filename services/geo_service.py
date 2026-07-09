"""Lightweight geo helpers for map pins.

Uses real latitude/longitude when present; otherwise tries optional
Nominatim (OpenStreetMap) geocoding, then falls back to a stable
approximate pin from address/neighborhood keywords and property id.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Simple process-level cache for Nominatim results
_NOMINATIM_CACHE: Dict[str, Optional[Tuple[float, float]]] = {}
_LAST_NOMINATIM_CALL = 0.0

# City / area centroids (lat, lng)
CITY_CENTERS: Dict[str, Tuple[float, float]] = {
    "tehran": (35.6892, 51.3890),
    "تهران": (35.6892, 51.3890),
    "mashhad": (36.2605, 59.6168),
    "مشهد": (36.2605, 59.6168),
    "isfahan": (32.6539, 51.6660),
    "اصفهان": (32.6539, 51.6660),
    "shiraz": (29.5918, 52.5837),
    "شیراز": (29.5918, 52.5837),
    "tabriz": (38.0962, 46.2738),
    "تبریز": (38.0962, 46.2738),
    "karaj": (35.8400, 50.9391),
    "کرج": (35.8400, 50.9391),
    "downtown": (40.7128, -74.0060),
    "suburbs": (40.7580, -73.9855),
    "beverly": (34.0736, -118.4004),
    "los angeles": (34.0522, -118.2437),
    "new york": (40.7128, -74.0060),
}

# Tehran district hints (relative offsets from Tehran center)
TEHRAN_DISTRICTS: Dict[str, Tuple[float, float]] = {
    "نیاوران": (0.06, 0.02),
    "فرشته": (0.04, 0.01),
    "الهیه": (0.045, 0.015),
    "زعفرانیه": (0.05, 0.01),
    "سعادت": (0.055, 0.02),
    "پاسداران": (0.04, 0.04),
    "جردن": (0.03, 0.0),
    "ونک": (0.02, -0.01),
    "تجریش": (0.07, 0.01),
    "طبرسی": (0.02, 0.03),
    "گاز": (0.015, 0.025),
    "صدف": (0.01, -0.02),
    "ساجدی": (0.01, 0.02),
}


def _stable_jitter(seed: str, scale: float = 0.012) -> Tuple[float, float]:
    """Deterministic small offset so pins don't stack."""
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    a = int(digest[:8], 16) / 0xFFFFFFFF
    b = int(digest[8:16], 16) / 0xFFFFFFFF
    return (a - 0.5) * 2 * scale, (b - 0.5) * 2 * scale


def _text_blob(prop: Any) -> str:
    parts = [
        str(getattr(prop, "address", "") or ""),
        str(getattr(prop, "neighborhood", "") or ""),
        str(getattr(prop, "title", "") or ""),
    ]
    return " ".join(parts).strip()


def nominatim_geocode(query: str, *, timeout: float = 4.0) -> Optional[Tuple[float, float]]:
    """Geocode a free-text query via OpenStreetMap Nominatim.

    Disabled when GEOCODE_PROVIDER is not nominatim/auto (default: auto).
    Respects ~1 req/sec polite usage. Returns None on failure.
    """
    global _LAST_NOMINATIM_CALL

    provider = (os.environ.get("GEOCODE_PROVIDER") or "auto").strip().lower()
    if provider in ("off", "none", "disabled", "approx"):
        return None

    q = (query or "").strip()
    if len(q) < 5:
        return None

    cache_key = q.lower()
    if cache_key in _NOMINATIM_CACHE:
        return _NOMINATIM_CACHE[cache_key]

    # Rate limit
    elapsed = time.time() - _LAST_NOMINATIM_CALL
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)

    params = urllib.parse.urlencode(
        {
            "q": q,
            "format": "json",
            "limit": "1",
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": os.environ.get(
                "GEOCODE_USER_AGENT",
                "PlatinumHeritageCRM/1.0 (local-dev; contact=admin@localhost)",
            )
        },
    )
    try:
        _LAST_NOMINATIM_CALL = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        if not data:
            _NOMINATIM_CACHE[cache_key] = None
            return None
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        result = (lat, lon)
        _NOMINATIM_CACHE[cache_key] = result
        return result
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.debug("Nominatim geocode failed for %r: %s", q[:80], exc)
        _NOMINATIM_CACHE[cache_key] = None
        return None
    except Exception as exc:  # pragma: no cover
        logger.warning("Nominatim unexpected error: %s", exc)
        _NOMINATIM_CACHE[cache_key] = None
        return None


def estimate_coordinates(prop: Any, *, try_nominatim: bool = False) -> Dict[str, Any]:
    """Return lat/lng for map display.

    Keys: latitude, longitude, approx (bool), source (str)
    """
    lat = getattr(prop, "latitude", None)
    lng = getattr(prop, "longitude", None)
    try:
        if lat is not None and lng is not None:
            lat_f, lng_f = float(lat), float(lng)
            if lat_f != 0 or lng_f != 0:
                return {
                    "latitude": lat_f,
                    "longitude": lng_f,
                    "approx": False,
                    "source": "stored",
                }
    except (TypeError, ValueError):
        pass

    text = _text_blob(prop)
    text_lower = text.lower()
    prop_id = getattr(prop, "id", 0) or 0

    if try_nominatim and text:
        hit = nominatim_geocode(text)
        if hit:
            return {
                "latitude": round(hit[0], 6),
                "longitude": round(hit[1], 6),
                "approx": False,
                "source": "nominatim",
            }

    # Match known cities
    base_lat, base_lng = 35.6892, 51.3890  # default Tehran (common for this inventory)
    source = "approx_tehran_default"

    for key, (clat, clng) in CITY_CENTERS.items():
        if key in text_lower or key in text:
            base_lat, base_lng = clat, clng
            source = f"approx_city:{key}"
            break

    # Tehran district offsets
    for key, (dlat, dlng) in TEHRAN_DISTRICTS.items():
        if key in text:
            base_lat += dlat
            base_lng += dlng
            source = f"approx_district:{key}"
            break

    # US-style simple street addresses → keep US downtown default if purely latin address
    if re.search(r"\b(st|street|ave|avenue|rd|road|ln|lane)\b", text_lower) and not re.search(
        r"[\u0600-\u06FF]", text
    ):
        if "approx_city" not in source and source == "approx_tehran_default":
            base_lat, base_lng = 40.7580, -73.9855
            source = "approx_us_default"

    jlat, jlng = _stable_jitter(f"{prop_id}:{text}", scale=0.018)
    return {
        "latitude": round(base_lat + jlat, 6),
        "longitude": round(base_lng + jlng, 6),
        "approx": True,
        "source": source,
    }


def serialize_for_map(prop: Any) -> Dict[str, Any]:
    """Property dict for Leaflet map payloads."""
    geo = estimate_coordinates(prop)
    return {
        "id": getattr(prop, "id", None),
        "title": getattr(prop, "title", "") or "Property",
        "address": getattr(prop, "address", "") or "",
        "neighborhood": getattr(prop, "neighborhood", "") or "",
        "price": getattr(prop, "price", 0) or 0,
        "property_type": getattr(prop, "property_type", "") or "",
        "listing_type": getattr(prop, "listing_type", "") or "sale",
        "rahn": getattr(prop, "rahn", None),
        "ejare": getattr(prop, "ejare", None),
        "bedrooms": getattr(prop, "bedrooms", None),
        "square_feet": getattr(prop, "square_feet", None),
        "latitude": geo["latitude"],
        "longitude": geo["longitude"],
        "approx": geo["approx"],
        "geo_source": geo["source"],
        "file_code": getattr(prop, "file_code", None),
        "image_filename": getattr(prop, "image_filename", None),
        "status": getattr(prop, "status", None),
    }
