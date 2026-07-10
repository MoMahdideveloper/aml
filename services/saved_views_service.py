"""Saved views for CRM list filters (versioned allowlisted JSON, never SQL)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from database import db
from services.unified_search import (
    CUSTOMER_FILTER_KEYS,
    SAVED_VIEW_SCHEMA_VERSION,
)
from sqlalchemy_models import SavedView, _utcnow_naive
from utils.observability import log_event

MAX_NAME_LEN = 80
MAX_FILTER_JSON_LEN = 2000
ENTITY_SCOPES = frozenset({"customers", "properties", "deals", "tasks", "agents"})


class SavedViewError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def canonicalize_filters(entity_scope: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    entity_scope = (entity_scope or "").strip().lower()
    if entity_scope not in ENTITY_SCOPES:
        raise SavedViewError("bad_scope", "Invalid entity scope")
    allow = CUSTOMER_FILTER_KEYS if entity_scope == "customers" else frozenset(
        {"q", "status", "agent_id", "sort", "page"}
    )
    out: Dict[str, Any] = {"v": SAVED_VIEW_SCHEMA_VERSION}
    raw = raw or {}
    for k, v in raw.items():
        if k in ("v", "version"):
            continue
        if k not in allow:
            continue  # ignore unknown
        if v is None or v == "":
            continue
        if isinstance(v, str) and len(v) > 200:
            raise SavedViewError("filter_too_long", f"Filter {k} too long")
        out[k] = v
    blob = json.dumps(out, sort_keys=True, separators=(",", ":"))
    if len(blob) > MAX_FILTER_JSON_LEN:
        raise SavedViewError("filters_too_large", "Filter payload too large")
    return out


class SavedViewsService:
    def list_for_user(self, user_id: int, entity_scope: Optional[str] = None) -> List[SavedView]:
        q = SavedView.query.filter_by(owner_user_id=user_id)
        if entity_scope:
            q = q.filter_by(entity_scope=entity_scope)
        return q.order_by(SavedView.is_default.desc(), SavedView.name.asc()).all()

    def get_owned(self, view_id: int, user_id: int) -> SavedView:
        view = db.session.get(SavedView, view_id)
        if not view or view.owner_user_id != user_id:
            raise SavedViewError("forbidden", "View not found")
        return view

    def create(
        self,
        *,
        user_id: int,
        name: str,
        entity_scope: str,
        filters: Dict[str, Any],
        sort_spec: str = "relevance",
        is_default: bool = False,
    ) -> SavedView:
        name = (name or "").strip()
        if not name or len(name) > MAX_NAME_LEN:
            raise SavedViewError("bad_name", f"Name required (max {MAX_NAME_LEN})")
        entity_scope = (entity_scope or "").strip().lower()
        canon = canonicalize_filters(entity_scope, filters)
        # deterministic duplicate name: update existing
        existing = SavedView.query.filter_by(
            owner_user_id=user_id, entity_scope=entity_scope, name=name
        ).first()
        if existing:
            existing.filter_json = json.dumps(canon, sort_keys=True)
            existing.sort_spec = (sort_spec or "relevance")[:32]
            existing.updated_at = _utcnow_naive()
            if is_default:
                self._clear_default(user_id, entity_scope)
                existing.is_default = True
            db.session.commit()
            log_event("saved_view_updated", component="search", view_id=existing.id)
            return existing

        if is_default:
            self._clear_default(user_id, entity_scope)
        view = SavedView(
            owner_user_id=user_id,
            name=name,
            entity_scope=entity_scope,
            filter_json=json.dumps(canon, sort_keys=True),
            sort_spec=(sort_spec or "relevance")[:32],
            is_default=bool(is_default),
        )
        db.session.add(view)
        db.session.commit()
        log_event("saved_view_created", component="search", view_id=view.id)
        return view

    def update(
        self,
        view_id: int,
        user_id: int,
        *,
        name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        sort_spec: Optional[str] = None,
    ) -> SavedView:
        view = self.get_owned(view_id, user_id)
        if name is not None:
            name = name.strip()
            if not name or len(name) > MAX_NAME_LEN:
                raise SavedViewError("bad_name", "Invalid name")
            view.name = name
        if filters is not None:
            canon = canonicalize_filters(view.entity_scope, filters)
            view.filter_json = json.dumps(canon, sort_keys=True)
        if sort_spec is not None:
            view.sort_spec = sort_spec[:32]
        view.updated_at = _utcnow_naive()
        db.session.commit()
        return view

    def delete(self, view_id: int, user_id: int) -> None:
        view = self.get_owned(view_id, user_id)
        db.session.delete(view)
        db.session.commit()
        log_event("saved_view_deleted", component="search", view_id=view_id)

    def set_default(self, view_id: int, user_id: int) -> SavedView:
        view = self.get_owned(view_id, user_id)
        self._clear_default(user_id, view.entity_scope)
        view.is_default = True
        view.updated_at = _utcnow_naive()
        db.session.commit()
        return view

    def apply_payload(self, view: SavedView) -> Dict[str, Any]:
        try:
            data = json.loads(view.filter_json or "{}")
        except json.JSONDecodeError:
            data = {"v": SAVED_VIEW_SCHEMA_VERSION}
        return canonicalize_filters(view.entity_scope, data)

    def _clear_default(self, user_id: int, entity_scope: str) -> None:
        SavedView.query.filter_by(
            owner_user_id=user_id, entity_scope=entity_scope, is_default=True
        ).update({"is_default": False})


saved_views_service = SavedViewsService()
