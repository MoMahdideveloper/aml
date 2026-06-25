import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from sqlalchemy import or_

from database import db
from sqlalchemy_models import Property, PropertyActivityLog, SyncState
from utils.execution_tracer import log_execution


logger = logging.getLogger("services.maskan_live_service")


@log_execution
def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if not text:
            return default
        digits = re.sub(r"[^\d]", "", text)
        if not digits:
            return default
        return int(digits)
    except (TypeError, ValueError):
        return default


@log_execution
def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


@log_execution
def _truncate(value: Any, max_len: int, default: str = "") -> str:
    text = str(value if value is not None else default).strip()
    return text[:max_len]


@log_execution
def _normalize_listing_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"rent", "rental", "lease"}:
        return "rental"
    return "sale"


@log_execution
def _normalize_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "active"
    if text == "available":
        return "active"
    if text in {"deleted", "removed"}:
        return "inactive"
    return text[:20]


@log_execution
def _to_local_file_code(source_code: str) -> str:
    return _truncate(source_code, 20)


@log_execution
def _to_legacy_local_file_code(source_code: str) -> str:
    return _truncate(f"MKN-{source_code}", 20)


@log_execution
def _parse_custom_fields(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


@log_execution
def _candidate_paths(primary: str, fallback: str) -> List[str]:
    paths: List[str] = []
    for raw in (primary, fallback):
        normalized = str(raw or "").strip()
        if not normalized:
            continue
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        if normalized not in paths:
            paths.append(normalized)
    return paths


class MaskanLiveService:
    def __init__(self) -> None:
        self.base_url = (os.environ.get("MASKAN_LIVE_API_BASE_URL") or "").strip().rstrip("/")
        self.api_key = (os.environ.get("MASKAN_LIVE_API_KEY") or "").strip()
        self.api_key_header = (os.environ.get("MASKAN_LIVE_API_KEY_HEADER") or "X-API-Key").strip() or "X-API-Key"
        self.timeout_seconds = max(3, int(os.environ.get("MASKAN_LIVE_TIMEOUT_SECONDS", "15")))
        self.default_limit = max(1, min(_safe_int(os.environ.get("MASKAN_LIVE_INCREMENTAL_LIMIT"), default=200), 5000))

        changes_path = os.environ.get(
            "MASKAN_LIVE_CHANGES_PATH",
            "/api/v2/integrations/gptvli/properties/changes",
        )
        self.changes_paths = _candidate_paths(changes_path, "/v2/integrations/gptvli/properties/changes")
        self.search_paths = _candidate_paths("/api/v2/properties/search", "/v2/properties/search")

    @property
    @log_execution
    def is_enabled(self) -> bool:
        return bool(self.base_url)

    @log_execution
    def _build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    @log_execution
    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers[self.api_key_header] = self.api_key
        return headers

    @log_execution
    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        if not self.is_enabled:
            return {}, 0

        url = self._build_url(path)
        try:
            method_upper = method.upper()
            if method_upper == "GET":
                response = requests.get(
                    url=url,
                    params=params or {},
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
            elif method_upper == "POST":
                response = requests.post(
                    url=url,
                    json=payload or {},
                    params=params or {},
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
            else:
                response = requests.request(
                    method=method_upper,
                    url=url,
                    json=payload or {},
                    params=params or {},
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
        except requests.RequestException as exc:
            logger.warning("Maskan live %s failed for %s: %s", method.upper(), url, exc)
            return {}, 0

        if response.status_code >= 400:
            logger.warning(
                "Maskan live %s status %s for %s: %s",
                method.upper(),
                response.status_code,
                url,
                (response.text or "")[:300],
            )
            return {}, response.status_code
        try:
            body = response.json()
        except Exception:
            return {}, response.status_code
        return (body if isinstance(body, dict) else {}), response.status_code

    @log_execution
    def _request_json_candidates(
        self,
        method: str,
        paths: Sequence[str],
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        for path in paths:
            body, status_code = self._request_json(
                method=method,
                path=path,
                payload=payload,
                params=params,
            )
            if body:
                return body
            if status_code in {0, 404, 405, 500, 502, 503, 504}:
                continue
        return {}

    @log_execution
    def _post_json(self, path: str, payload: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body, _ = self._request_json("POST", path=path, payload=payload, params=params)
        return body

    @log_execution
    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        body, _ = self._request_json("GET", path=path, params=params)
        return body

    @log_execution
    def health(self) -> Dict[str, Any]:
        return self._get_json("/health")

    @log_execution
    def _build_search_payload(
        self,
        beds: Optional[int],
        sqm: Optional[int],
        min_price: Optional[int],
        max_price: Optional[int],
        property_type: Optional[str],
        location: Optional[str],
        top_k: int,
        page: int = 1,
    ) -> Dict[str, Any]:
        size = max(1, min(_safe_int(top_k, default=20), 100))
        return {
            "pagination": {
                "page": max(1, _safe_int(page, default=1)),
                "size": size,
            },
            "sort": {
                "field": "last_seen",
                "order": "desc",
            },
            "filters": {
                "listing_types": [],
                "enrichment_status": [],
                "financials": {
                    "min_price": _safe_int(min_price, default=0) or None,
                    "max_price": _safe_int(max_price, default=0) or None,
                    "min_deposit": None,
                    "max_deposit": None,
                    "min_rent": None,
                    "max_rent": None,
                },
                "specs": {
                    "min_area": _safe_int(sqm, default=0) or None,
                    "max_area": None,
                    "bedrooms": _safe_int(beds, default=0) or None,
                    "age_min": None,
                    "age_max": None,
                    "has_elevator": None,
                    "has_parking": None,
                    "has_storage": None,
                    "has_balcony": None,
                    "property_types": [str(property_type).strip()] if str(property_type or "").strip() else [],
                },
                "location": {
                    "zones": [],
                    "neighborhood": str(location).strip() if str(location or "").strip() else None,
                    "search": str(location).strip() if str(location or "").strip() else None,
                },
            },
        }

    @log_execution
    def _map_external_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        location = str(item.get("location") or "").strip()
        total_price_text = item.get("total_price")
        price_numeric = _safe_int(item.get("price_numeric"), default=0)
        if price_numeric <= 0:
            price_numeric = _safe_int(total_price_text, default=0)

        rent_value = _safe_int(item.get("rent"), default=0)
        deposit_value = _safe_int(item.get("deposit"), default=0)
        bathrooms = _safe_int(item.get("bathrooms"), default=0)
        if bathrooms <= 0:
            bathrooms = _safe_int(payload.get("bathrooms"), default=0)
            if bathrooms <= 0:
                bathrooms = _safe_int(payload.get("bathroom"), default=0)

        return {
            "external_code": _truncate(item.get("code"), 64),
            "id": None,
            "title": item.get("title") or f"Maskan Listing {item.get('code')}",
            "property_type": item.get("property_type") or payload.get("property_type") or "apartment",
            "listing_type": _normalize_listing_type(item.get("listing_type")),
            "price": price_numeric,
            "bedrooms": _safe_int(item.get("bedrooms"), default=0),
            "bathrooms": bathrooms,
            "square_feet": _safe_int(item.get("area"), default=0),
            "neighborhood": location,
            "description": item.get("ai_description") or payload.get("description") or "Synced from Maskan live API.",
            "rahn": deposit_value or None,
            "ejare": rent_value or None,
            "status": "active",
            "source": "maskan_live_api",
        }

    @log_execution
    def _map_change_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        source_code = _truncate(item.get("source_code") or item.get("code") or item.get("file_code"), 64)
        raw_payload = item.get("payload") if isinstance(item.get("payload"), dict) else None

        return {
            "external_code": source_code,
            "title": _truncate(item.get("title") or f"Maskan Listing {source_code}", 255),
            "address": _truncate(item.get("address"), 2000),
            "listing_type": _normalize_listing_type(item.get("listing_type")),
            "price": _safe_int(item.get("price"), default=0),
            "rahn": _safe_int(item.get("rahn"), default=0) or None,
            "ejare": _safe_int(item.get("ejare"), default=0) or None,
            "property_type": _truncate(item.get("property_type") or "apartment", 50),
            "bedrooms": _safe_int(item.get("bedrooms"), default=0),
            "bathrooms": _safe_int(item.get("bathrooms"), default=0),
            "square_feet": _safe_int(item.get("square_feet"), default=0),
            "built_area": _safe_int(item.get("built_area"), default=0) or None,
            "land_area": _safe_int(item.get("land_area"), default=0) or None,
            "description": _truncate(item.get("description") or "Synced from Maskan live API.", 10000),
            "status": _normalize_status(item.get("status")),
            "year_built": _safe_int(item.get("year_built"), default=0) or None,
            "parking_spaces": _safe_int(item.get("parking_spaces"), default=0),
            "floors": _safe_int(item.get("floors"), default=0),
            "units": _safe_int(item.get("units"), default=0),
            "floor_number": _safe_int(item.get("floor_number"), default=0) or None,
            "has_storage": _safe_bool(item.get("has_storage"), default=False),
            "has_elevator": _safe_bool(item.get("has_elevator"), default=False),
            "document_type": _truncate(item.get("document_type"), 50),
            "floor_covering": _truncate(item.get("floor_covering"), 50),
            "facade_type": _truncate(item.get("facade_type"), 50),
            "wall_covering": _truncate(item.get("wall_covering"), 50),
            "cabinet_type": _truncate(item.get("cabinet_type"), 50),
            "property_direction": _truncate(item.get("property_direction"), 30),
            "is_exchangeable": _safe_bool(item.get("is_exchangeable"), default=False),
            "price_per_meter": _safe_int(item.get("price_per_meter"), default=0) or None,
            "property_features": _truncate(item.get("property_features"), 10000),
            "owner_name": _truncate(item.get("owner_name"), 255),
            "owner_phone": _truncate(item.get("owner_phone"), 255),
            "enrichment_status": _truncate(item.get("enrichment_status"), 64),
            "has_phone": _safe_bool(item.get("has_phone"), default=False),
            "source_updated_at": _truncate(item.get("source_updated_at"), 64),
            "source_last_seen": _truncate(item.get("source_last_seen"), 64),
            "payload": raw_payload,
            "source": "maskan_live_api",
        }

    @log_execution
    def search_properties(
        self,
        beds: Optional[int] = None,
        sqm: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        property_type: Optional[str] = None,
        location: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        if not self.is_enabled:
            return []

        body = self._build_search_payload(
            beds=beds,
            sqm=sqm,
            min_price=min_price,
            max_price=max_price,
            property_type=property_type,
            location=location,
            top_k=top_k,
            page=1,
        )
        response = self._request_json_candidates(
            method="POST",
            paths=self.search_paths,
            payload=body,
            params={"include_pii": "false"},
        )
        items = response.get("items") if isinstance(response.get("items"), list) else []
        mapped = [self._map_external_item(item) for item in items if isinstance(item, dict)]
        return mapped[: max(1, min(_safe_int(top_k, default=10), 100))]

    @log_execution
    def fetch_property_changes(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        fetch_all: bool = False,
        include_pii: bool = False,
        include_payload: bool = False,
    ) -> Dict[str, Any]:
        if not self.is_enabled:
            return {}

        effective_limit = max(1, min(_safe_int(limit, default=self.default_limit), 5000))
        params: Dict[str, Any] = {
            "include_pii": "true" if include_pii else "false",
            "include_payload": "true" if include_payload else "false",
        }
        if fetch_all:
            params["fetch_all"] = "true"
        elif page is not None or page_size is not None:
            params["page"] = max(1, _safe_int(page, default=1))
            params["page_size"] = max(1, min(_safe_int(page_size, default=effective_limit), 5000))
        else:
            params["limit"] = effective_limit
            if cursor:
                params["cursor"] = cursor

        response = self._request_json_candidates(
            method="GET",
            paths=self.changes_paths,
            params=params,
        )
        items = response.get("items") if isinstance(response.get("items"), list) else []
        return {
            "items": items,
            "count": _safe_int(response.get("count"), default=len(items)),
            "limit": _safe_int(response.get("limit"), default=effective_limit),
            "has_more": _safe_bool(response.get("has_more"), default=False),
            "next_cursor": _truncate(response.get("next_cursor"), 255) or None,
            "generated_at": _truncate(response.get("generated_at"), 64),
        }

    @log_execution
    def _find_property_by_source_code(self, source_code: str) -> Optional[Property]:
        canonical = _to_local_file_code(source_code)
        legacy = _to_legacy_local_file_code(source_code)
        return (
            Property.query.filter(or_(Property.file_code == canonical, Property.file_code == legacy))
            .order_by(Property.id.desc())
            .first()
        )

    # Fields tracked for change detection during sync
    TRACKED_FIELDS = [
        'title', 'price', 'listing_type', 'property_type', 'bedrooms',
        'square_feet', 'built_area', 'land_area', 'year_built',
        'parking_spaces', 'floors', 'units', 'floor_number',
        'has_storage', 'has_elevator', 'is_exchangeable', 'price_per_meter',
        'document_type', 'floor_covering', 'facade_type', 'wall_covering',
        'cabinet_type', 'property_direction', 'rahn', 'ejare',
        'address', 'description', 'status', 'property_features',
    ]

    @log_execution
    def _upsert_property(
        self,
        mapped: Dict[str, Any],
        overwrite: bool,
        now_iso: str,
        include_payload: bool = False,
        sync_version: Optional[int] = None,
    ) -> Tuple[int, int, int]:
        """Upsert a property and log field-level changes.

        Returns (created, updated, fields_changed) counts.
        """
        source_code = _truncate(mapped.get("external_code"), 64)
        if not source_code:
            return 0, 0, 0

        canonical_file_code = _to_local_file_code(source_code)
        property_obj = self._find_property_by_source_code(source_code)
        created = 0
        updated = 0
        fields_changed = 0

        if property_obj is None:
            property_obj = Property(
                title=_truncate(mapped.get("title"), 255, default=f"Maskan Listing {source_code}"),
                address=_truncate(mapped.get("address"), 2000),
                price=_safe_int(mapped.get("price"), default=0),
                property_type=_truncate(mapped.get("property_type"), 50, default="apartment"),
                bedrooms=_safe_int(mapped.get("bedrooms"), default=0),
                bathrooms=_safe_int(mapped.get("bathrooms"), default=0),
                square_feet=_safe_int(mapped.get("square_feet"), default=0),
                description=_truncate(mapped.get("description"), 10000, default="Synced from Maskan live API."),
                status=_normalize_status(mapped.get("status")),
                listing_type=_normalize_listing_type(mapped.get("listing_type")),
                rahn=_safe_int(mapped.get("rahn"), default=0) or None,
                ejare=_safe_int(mapped.get("ejare"), default=0) or None,
                file_code=canonical_file_code,
                source="maskan",
            )
            db.session.add(property_obj)
            created = 1
        else:
            updated = 1
            if property_obj.is_deleted:
                property_obj.is_deleted = False
                property_obj.deleted_at = None

        if not property_obj.file_code:
            property_obj.file_code = canonical_file_code

        # ── Field-level change detection ──
        # Build a dict of what the new values WILL be after this upsert
        new_values: Dict[str, Any] = {
            'listing_type': _normalize_listing_type(mapped.get("listing_type")),
            'status': _normalize_status(mapped.get("status")),
            'price': _safe_int(mapped.get("price"), default=0),
            'rahn': _safe_int(mapped.get("rahn"), default=0) or None,
            'ejare': _safe_int(mapped.get("ejare"), default=0) or None,
            'bedrooms': _safe_int(mapped.get("bedrooms"), default=0),
            'square_feet': _safe_int(mapped.get("square_feet"), default=0),
            'built_area': _safe_int(mapped.get("built_area"), default=0) or None,
            'land_area': _safe_int(mapped.get("land_area"), default=0) or None,
            'year_built': _safe_int(mapped.get("year_built"), default=0) or None,
            'parking_spaces': _safe_int(mapped.get("parking_spaces"), default=0),
            'floors': max(0, _safe_int(mapped.get("floors"), default=0)),
            'units': max(0, _safe_int(mapped.get("units"), default=0)),
            'floor_number': _safe_int(mapped.get("floor_number"), default=0) or None,
            'has_storage': _safe_bool(mapped.get("has_storage"), default=False),
            'has_elevator': _safe_bool(mapped.get("has_elevator"), default=False),
            'is_exchangeable': _safe_bool(mapped.get("is_exchangeable"), default=False),
            'price_per_meter': _safe_int(mapped.get("price_per_meter"), default=0) or None,
            'property_features': _truncate(mapped.get("property_features"), 10000),
        }

        # For new properties, skip change detection (all fields are new)
        if created == 0:
            for field in self.TRACKED_FIELDS:
                if field not in new_values:
                    continue
                old_val = getattr(property_obj, field, None)
                new_val = new_values[field]
                if str(old_val) != str(new_val) and new_val is not None:
                    try:
                        db.session.add(PropertyActivityLog(
                            property_id=property_obj.id,
                            action=f"{field}_changed",
                            description=f"Sync updated {field}",
                            old_value=str(old_val) if old_val is not None else None,
                            new_value=str(new_val),
                            change_source="sync",
                            changed_by="system",
                            sync_version=sync_version,
                        ))
                        fields_changed += 1
                    except Exception as exc:
                        logger.debug("Failed to log change for %s.%s: %s", source_code, field, exc)

        # ── Apply values ──
        property_obj.listing_type = new_values['listing_type']
        property_obj.status = new_values['status']
        property_obj.price = new_values['price']
        property_obj.rahn = new_values['rahn']
        property_obj.ejare = new_values['ejare']
        property_obj.bedrooms = new_values['bedrooms']
        property_obj.square_feet = new_values['square_feet']
        property_obj.built_area = new_values['built_area']
        property_obj.land_area = new_values['land_area']
        property_obj.year_built = new_values['year_built']
        property_obj.parking_spaces = new_values['parking_spaces']
        property_obj.floors = new_values['floors']
        property_obj.units = new_values['units']
        property_obj.floor_number = new_values['floor_number']
        property_obj.has_storage = new_values['has_storage']
        property_obj.has_elevator = new_values['has_elevator']
        property_obj.is_exchangeable = new_values['is_exchangeable']
        property_obj.price_per_meter = new_values['price_per_meter']
        property_obj.property_features = new_values['property_features']

        if overwrite or not property_obj.title:
            new_title = _truncate(mapped.get("title"), 255, default=property_obj.title)
            if created == 0 and str(property_obj.title) != str(new_title):
                try:
                    db.session.add(PropertyActivityLog(
                        property_id=property_obj.id,
                        action="title_changed",
                        description="Sync updated title",
                        old_value=property_obj.title,
                        new_value=new_title,
                        change_source="sync",
                        changed_by="system",
                        sync_version=sync_version,
                    ))
                    fields_changed += 1
                except Exception:
                    pass
            property_obj.title = new_title
        if overwrite or not property_obj.address:
            property_obj.address = _truncate(mapped.get("address"), 2000, default=property_obj.address)
        if overwrite or not property_obj.description:
            property_obj.description = _truncate(mapped.get("description"), 10000, default=property_obj.description)
        if overwrite or not property_obj.property_type:
            property_obj.property_type = _truncate(mapped.get("property_type"), 50, default=property_obj.property_type)
        if overwrite or not property_obj.document_type:
            property_obj.document_type = _truncate(mapped.get("document_type"), 50)
        if overwrite or not property_obj.floor_covering:
            property_obj.floor_covering = _truncate(mapped.get("floor_covering"), 50)
        if overwrite or not property_obj.facade_type:
            property_obj.facade_type = _truncate(mapped.get("facade_type"), 50)
        if overwrite or not property_obj.wall_covering:
            property_obj.wall_covering = _truncate(mapped.get("wall_covering"), 50)
        if overwrite or not property_obj.cabinet_type:
            property_obj.cabinet_type = _truncate(mapped.get("cabinet_type"), 50)
        if overwrite or not property_obj.property_direction:
            property_obj.property_direction = _truncate(mapped.get("property_direction"), 30)

        custom_fields = _parse_custom_fields(property_obj.custom_fields)
        custom_fields.update(
            {
                "external_source": "maskan_live_api",
                "external_code": source_code,
                "external_last_sync_at": now_iso,
                "external_source_updated_at": _truncate(mapped.get("source_updated_at"), 64),
                "external_source_last_seen": _truncate(mapped.get("source_last_seen"), 64),
                "external_enrichment_status": _truncate(mapped.get("enrichment_status"), 64),
                "external_has_phone": _safe_bool(mapped.get("has_phone"), default=False),
                "external_owner_name": _truncate(mapped.get("owner_name"), 255),
                "external_owner_phone": _truncate(mapped.get("owner_phone"), 255),
            }
        )
        if include_payload and isinstance(mapped.get("payload"), dict):
            custom_fields["external_payload"] = mapped.get("payload")
        property_obj.custom_fields = json.dumps(custom_fields, ensure_ascii=False)

        return created, updated, fields_changed

    @log_execution
    def sync_properties_to_local_db(
        self,
        max_pages: int = 1,
        page_size: int = 200,
        listing_type: Optional[str] = None,
        zone: Optional[int] = None,
        overwrite: bool = True,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        fetch_all: bool = False,
        include_pii: bool = False,
        include_payload: bool = False,
    ) -> Dict[str, Any]:
        if not self.is_enabled:
            return {"created": 0, "updated": 0, "fetched": 0, "synced": 0, "pages": 0, "enabled": False}

        import time as _time
        sync_start = _time.monotonic()

        # ── Create SyncState record ──
        sync_record = SyncState(status="running")
        try:
            db.session.add(sync_record)
            db.session.flush()  # get the id
            sync_version = sync_record.id
        except Exception:
            sync_version = None
            sync_record = None

        # Retained for backward compatibility with old callers. The changes endpoint has no zone filter.
        _ = zone

        # ── If no cursor provided, try to use last successful sync cursor ──
        if cursor is None and sync_record is not None:
            try:
                last_success = (
                    SyncState.query
                    .filter(SyncState.status == "completed")
                    .order_by(SyncState.id.desc())
                    .first()
                )
                if last_success and last_success.last_sync_cursor:
                    cursor = last_success.last_sync_cursor
            except Exception:
                pass

        page_limit = max(1, min(_safe_int(max_pages, default=1), 5000))
        size = max(1, min(_safe_int(limit, default=_safe_int(page_size, default=self.default_limit)), 5000))
        normalized_listing_type = str(listing_type or "").strip().lower()
        if normalized_listing_type in {"rent", "rental", "lease"}:
            listing_type_filter = "rental"
        elif normalized_listing_type == "sale":
            listing_type_filter = "sale"
        else:
            listing_type_filter = ""

        created = 0
        updated = 0
        fetched = 0
        synced = 0
        total_fields_changed = 0
        pages_processed = 0
        has_more = False
        next_cursor: Optional[str] = _truncate(cursor, 255) or None
        now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        try:
            if fetch_all:
                batches = [
                    self.fetch_property_changes(
                        fetch_all=True,
                        include_pii=include_pii,
                        include_payload=include_payload,
                    )
                ]
                mode = "fetch_all"
            elif next_cursor is not None or page_limit == 1:
                batches = []
                mode = "cursor"
                current_cursor = next_cursor
                for _idx in range(page_limit):
                    payload = self.fetch_property_changes(
                        cursor=current_cursor,
                        limit=size,
                        include_pii=include_pii,
                        include_payload=include_payload,
                    )
                    batches.append(payload)
                    current_cursor = _truncate(payload.get("next_cursor"), 255) or current_cursor
                    next_cursor = current_cursor
                    has_more = _safe_bool(payload.get("has_more"), default=False)
                    if not has_more:
                        break
            else:
                batches = []
                mode = "page"
                for page in range(1, page_limit + 1):
                    payload = self.fetch_property_changes(
                        page=page,
                        page_size=size,
                        include_pii=include_pii,
                        include_payload=include_payload,
                    )
                    batches.append(payload)
                    has_more = _safe_bool(payload.get("has_more"), default=False)
                    if not payload.get("items") or not has_more:
                        break

            for payload in batches:
                items = payload.get("items") if isinstance(payload.get("items"), list) else []
                if not items:
                    continue
                pages_processed += 1
                fetched += len(items)
                next_cursor = _truncate(payload.get("next_cursor"), 255) or next_cursor
                has_more = _safe_bool(payload.get("has_more"), default=has_more)

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    mapped = self._map_change_item(item)
                    if listing_type_filter and mapped.get("listing_type") != listing_type_filter:
                        continue
                    row_created, row_updated, row_fields = self._upsert_property(
                        mapped=mapped,
                        overwrite=overwrite,
                        now_iso=now_iso,
                        include_payload=include_payload,
                        sync_version=sync_version,
                    )
                    created += row_created
                    updated += row_updated
                    total_fields_changed += row_fields
                    if row_created or row_updated:
                        synced += 1

            # ── Update SyncState on success ──
            if sync_record is not None:
                sync_record.status = "completed"
                sync_record.last_sync_at = datetime.now(UTC).replace(tzinfo=None)
                sync_record.last_sync_cursor = next_cursor
                sync_record.properties_synced = synced
                sync_record.properties_created = created
                sync_record.properties_updated = updated
                sync_record.fields_changed = total_fields_changed
                sync_record.duration_seconds = round(_time.monotonic() - sync_start, 2)

        except Exception as exc:
            if sync_record is not None:
                sync_record.status = "failed"
                sync_record.error_message = str(exc)[:2000]
                sync_record.duration_seconds = round(_time.monotonic() - sync_start, 2)
            logger.exception("Sync failed: %s", exc)

        db.session.commit()
        return {
            "enabled": True,
            "mode": mode if 'mode' in dir() else "unknown",
            "created": created,
            "updated": updated,
            "fetched": fetched,
            "synced": synced,
            "fields_changed": total_fields_changed,
            "pages": pages_processed,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "cursor_used": _truncate(cursor, 255) or None,
            "limit": size,
            "sync_version": sync_version,
        }


maskan_live_service = MaskanLiveService()
