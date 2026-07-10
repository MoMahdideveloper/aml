"""Import validation, duplicate detection, execution, and guarded rollback."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from database import db
from services.import_parser import ParsedCSV, parse_csv_bytes
from sqlalchemy_models import (
    Agent,
    Customer,
    Deal,
    ImportBatch,
    ImportRowResult,
    Property,
    _utcnow_naive,
)
from utils.observability import log_event, record_business_counter

ENTITY_FIELDS = {
    "customer": [
        "name",
        "email",
        "phone",
        "budget_min",
        "budget_max",
        "preferred_bedrooms",
        "preferred_bathrooms",
        "preferred_type",
        "location_preference",
        "status",
        "customer_type",
        "preferences",
        "external_id",
    ],
    "property": [
        "title",
        "address",
        "property_type",
        "price",
        "bedrooms",
        "bathrooms",
        "square_feet",
        "description",
        "status",
        "agent_id",
        "agent_email",
        "listing_type",
        "neighborhood",
        "file_code",
        "year_built",
    ],
    "deal": [
        "property_id",
        "property_file_code",
        "customer_id",
        "customer_email",
        "agent_id",
        "agent_email",
        "status",
        "offer_amount",
        "notes",
        "external_id",
    ],
}

REQUIRED = {
    "customer": ["name", "email", "phone"],
    "property": ["title", "address", "property_type"],
    "deal": [],  # resolved via id or alternate keys
}

CUSTOMER_TYPES = {"buyer", "seller", "both", "investor"}
CUSTOMER_STATUS = {"active", "prospect", "lead", "inactive"}
LISTING_TYPES = {"sale", "rental", "rent", "lease"}


def _norm_email(v: str) -> str:
    return (v or "").strip().lower()


def _norm_phone(v: str) -> str:
    digits = re.sub(r"\D+", "", v or "")
    return digits


def _norm_address(v: str) -> str:
    s = (v or "").strip().lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _to_int(v: str, default: Optional[int] = 0) -> Optional[int]:
    if v is None or str(v).strip() == "":
        return default
    s = str(v).replace(",", "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def temp_import_dir() -> Path:
    root = Path("instance") / "imports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cleanup_temp(path: str) -> None:
    if not path:
        return
    p = Path(path)
    try:
        if p.is_file():
            p.unlink(missing_ok=True)
    except OSError:
        pass


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


@dataclass
class RowClassification:
    outcome: str
    error_codes: str = ""
    diagnostic: str = ""
    match_key: str = ""
    payload: Dict[str, Any] = None
    existing_id: Optional[int] = None

    def __post_init__(self):
        if self.payload is None:
            self.payload = {}


class ImportService:
    def create_batch_from_upload(
        self,
        *,
        entity_type: str,
        filename: str,
        data: bytes,
        uploader_id: Optional[int],
        uploader_label: str,
    ) -> ImportBatch:
        entity_type = (entity_type or "").strip().lower()
        if entity_type not in ENTITY_FIELDS:
            raise ValueError("Unsupported entity type")

        parsed = parse_csv_bytes(data)
        # Idempotency: completed identical batch
        existing = (
            ImportBatch.query.filter_by(
                file_hash=parsed.file_hash,
                entity_type=entity_type,
                status="completed",
            )
            .order_by(ImportBatch.id.desc())
            .first()
        )
        if existing:
            raise ValueError(
                f"Identical file already imported as batch #{existing.id}. "
                "Upload a different file or request explicit re-run."
            )

        dest = temp_import_dir() / f"{parsed.file_hash[:16]}_{os.getpid()}.csv"
        dest.write_bytes(data)

        batch = ImportBatch(
            entity_type=entity_type,
            status="uploaded",
            original_filename=(filename or "upload.csv")[:255],
            file_hash=parsed.file_hash,
            uploader_id=uploader_id,
            uploader_label=(uploader_label or "")[:120],
            total_rows=parsed.raw_row_count,
            temp_path=str(dest),
            mapping_json="{}",
            mode="create_only",
        )
        db.session.add(batch)
        db.session.commit()
        log_event(
            "import_uploaded",
            component="import",
            batch_id=batch.id,
            entity_type=entity_type,
            total_rows=parsed.raw_row_count,
        )
        return batch

    def save_mapping(self, batch: ImportBatch, mapping: Dict[str, str]) -> None:
        # mapping: crm_field -> csv_header
        allowed = set(ENTITY_FIELDS[batch.entity_type])
        clean: Dict[str, str] = {}
        used_headers = set()
        for dest, src in mapping.items():
            dest = (dest or "").strip()
            src = (src or "").strip().lower()
            if not dest or dest not in allowed:
                continue
            if not src:
                continue
            if src in used_headers:
                raise ValueError(f"Duplicate source mapping for header {src}")
            used_headers.add(src)
            clean[dest] = src
        for req in REQUIRED.get(batch.entity_type, []):
            if req not in clean:
                # deal uses alternate keys
                if batch.entity_type == "deal":
                    continue
                raise ValueError(f"Required field not mapped: {req}")
        if batch.entity_type == "deal":
            if "property_id" not in clean and "property_file_code" not in clean:
                raise ValueError("Map property_id or property_file_code")
            if "customer_id" not in clean and "customer_email" not in clean:
                raise ValueError("Map customer_id or customer_email")

        batch.mapping_json = json.dumps(clean)
        batch.status = "mapped"
        db.session.commit()

    def _map_row(self, batch: ImportBatch, raw: Dict[str, str]) -> Dict[str, str]:
        mapping = json.loads(batch.mapping_json or "{}")
        out: Dict[str, str] = {}
        for dest, src in mapping.items():
            out[dest] = raw.get(src, "")
        return out

    def validate_and_classify_row(
        self, batch: ImportBatch, row_number: int, raw: Dict[str, str]
    ) -> RowClassification:
        mapped = self._map_row(batch, raw)
        if batch.entity_type == "customer":
            return self._classify_customer(mapped, row_number)
        if batch.entity_type == "property":
            return self._classify_property(mapped, row_number)
        if batch.entity_type == "deal":
            return self._classify_deal(mapped, row_number)
        return RowClassification("invalid", "unknown_entity", "Unknown entity")

    def _classify_customer(self, m: Dict[str, str], row_number: int) -> RowClassification:
        errors = []
        name = (m.get("name") or "").strip()
        email = _norm_email(m.get("email") or "")
        phone = _norm_phone(m.get("phone") or "")
        if not name:
            errors.append("name_required")
        if not email or "@" not in email:
            errors.append("email_invalid")
        if not phone or len(phone) < 7:
            errors.append("phone_invalid")
        budget_min = _to_int(m.get("budget_min") or "0", 0)
        budget_max = _to_int(m.get("budget_max") or "0", 0)
        if budget_min is None or budget_max is None or budget_min < 0 or budget_max < 0:
            errors.append("budget_invalid")
        ctype = (m.get("customer_type") or "buyer").strip().lower() or "buyer"
        if ctype not in CUSTOMER_TYPES:
            errors.append("customer_type_invalid")
        status = (m.get("status") or "active").strip().lower() or "active"
        if status not in CUSTOMER_STATUS:
            errors.append("status_invalid")
        if errors:
            return RowClassification(
                "invalid",
                ",".join(errors),
                "Validation failed",
                match_key=email or phone,
            )

        payload = {
            "name": name,
            "email": email,
            "phone": phone,
            "budget_min": budget_min or 0,
            "budget_max": budget_max or 0,
            "preferred_bedrooms": _to_int(m.get("preferred_bedrooms") or "0", 0) or 0,
            "preferred_bathrooms": _to_int(m.get("preferred_bathrooms") or "0", 0) or 0,
            "preferred_type": (m.get("preferred_type") or "")[:50],
            "location_preference": (m.get("location_preference") or "")[:255],
            "status": status,
            "customer_type": ctype,
            "preferences": (m.get("preferences") or "")[:4000],
            "external_id": (m.get("external_id") or "")[:64],
        }

        existing = Customer.query.filter(
            Customer.is_deleted.is_(False),
            (Customer.email == email) | (Customer.phone == phone),
        ).first()
        # also match normalized phone against stored phones
        if not existing and phone:
            for c in Customer.query.filter(Customer.is_deleted.is_(False)).limit(2000):
                if _norm_phone(c.phone) == phone or _norm_email(c.email) == email:
                    existing = c
                    break
        if existing:
            return RowClassification(
                "exact_duplicate",
                "exact_email_or_phone",
                f"Matches customer #{existing.id}",
                match_key=email,
                payload=payload,
                existing_id=existing.id,
            )

        # possible duplicate by name
        possible = None
        best = 0.0
        for c in Customer.query.filter(Customer.is_deleted.is_(False)).limit(500):
            score = similarity(name, c.name or "")
            if score >= 0.92 and score > best:
                best = score
                possible = c
        if possible:
            return RowClassification(
                "possible_duplicate",
                "name_similarity",
                f"Possible match customer #{possible.id} score={best:.2f}",
                match_key=email,
                payload=payload,
                existing_id=possible.id,
            )

        return RowClassification("valid", "", "OK", match_key=email, payload=payload)

    def _classify_property(self, m: Dict[str, str], row_number: int) -> RowClassification:
        errors = []
        title = (m.get("title") or "").strip()
        address = (m.get("address") or "").strip()
        ptype = (m.get("property_type") or "").strip()
        if not title:
            errors.append("title_required")
        if not address:
            errors.append("address_required")
        if not ptype:
            errors.append("property_type_required")
        price = _to_int(m.get("price") or "0", 0)
        if price is None or price < 0:
            errors.append("price_invalid")
        listing = (m.get("listing_type") or "sale").strip().lower() or "sale"
        if listing not in LISTING_TYPES:
            errors.append("listing_type_invalid")
        agent_id = _to_int(m.get("agent_id") or "", None)
        agent_email = _norm_email(m.get("agent_email") or "")
        if agent_id is None and m.get("agent_id"):
            errors.append("agent_id_invalid")
        file_code = (m.get("file_code") or "").strip()
        if errors:
            return RowClassification("invalid", ",".join(errors), "Validation failed")

        if agent_id is None and agent_email:
            ag = Agent.query.filter_by(email=agent_email, is_deleted=False).first()
            if ag:
                agent_id = ag.id

        payload = {
            "title": title[:255],
            "address": address,
            "property_type": ptype[:50],
            "price": price or 0,
            "bedrooms": _to_int(m.get("bedrooms") or "0", 0) or 0,
            "bathrooms": _to_int(m.get("bathrooms") or "0", 0) or 0,
            "square_feet": _to_int(m.get("square_feet") or "0", 0) or 0,
            "description": (m.get("description") or "")[:4000],
            "status": (m.get("status") or "active")[:20],
            "agent_id": agent_id,
            "listing_type": listing if listing != "rent" else "rental",
            "neighborhood": (m.get("neighborhood") or "")[:100],
            "file_code": file_code[:20] or None,
            "year_built": _to_int(m.get("year_built") or "", None),
        }
        addr_n = _norm_address(address)
        if file_code:
            ex = Property.query.filter_by(file_code=file_code, is_deleted=False).first()
            if ex:
                return RowClassification(
                    "exact_duplicate",
                    "file_code",
                    f"Matches property #{ex.id}",
                    match_key=file_code,
                    payload=payload,
                    existing_id=ex.id,
                )
        for p in Property.query.filter(Property.is_deleted.is_(False)).limit(2000):
            if _norm_address(p.address or "") == addr_n and addr_n:
                return RowClassification(
                    "exact_duplicate",
                    "address",
                    f"Matches property #{p.id}",
                    match_key=addr_n[:120],
                    payload=payload,
                    existing_id=p.id,
                )

        possible = None
        best = 0.0
        for p in Property.query.filter(Property.is_deleted.is_(False)).limit(400):
            s = 0.5 * similarity(title, p.title or "") + 0.5 * similarity(
                addr_n, _norm_address(p.address or "")
            )
            if s >= 0.9 and s > best:
                best = s
                possible = p
        if possible:
            return RowClassification(
                "possible_duplicate",
                "title_address_similarity",
                f"Possible property #{possible.id} score={best:.2f}",
                match_key=addr_n[:120],
                payload=payload,
                existing_id=possible.id,
            )
        return RowClassification("valid", "", "OK", match_key=addr_n[:120], payload=payload)

    def _classify_deal(self, m: Dict[str, str], row_number: int) -> RowClassification:
        errors = []
        property_id = _to_int(m.get("property_id") or "", None)
        customer_id = _to_int(m.get("customer_id") or "", None)
        agent_id = _to_int(m.get("agent_id") or "", None)
        if m.get("property_id") and property_id is None:
            errors.append("property_id_invalid")
        if m.get("customer_id") and customer_id is None:
            errors.append("customer_id_invalid")
        pcode = (m.get("property_file_code") or "").strip()
        cemail = _norm_email(m.get("customer_email") or "")
        aemail = _norm_email(m.get("agent_email") or "")
        if property_id is None and pcode:
            p = Property.query.filter_by(file_code=pcode, is_deleted=False).first()
            if p:
                property_id = p.id
            else:
                errors.append("property_not_found")
        if customer_id is None and cemail:
            c = Customer.query.filter_by(email=cemail, is_deleted=False).first()
            if c:
                customer_id = c.id
            else:
                errors.append("customer_not_found")
        if agent_id is None and aemail:
            a = Agent.query.filter_by(email=aemail, is_deleted=False).first()
            if a:
                agent_id = a.id
        if property_id is None:
            errors.append("property_required")
        if customer_id is None:
            errors.append("customer_required")
        offer = _to_int(m.get("offer_amount") or "0", 0)
        if offer is None or offer < 0:
            errors.append("offer_invalid")
        status = (m.get("status") or "prospecting").strip() or "prospecting"
        external_id = (m.get("external_id") or "").strip()
        if errors:
            return RowClassification("invalid", ",".join(errors), "Validation failed")

        payload = {
            "property_id": property_id,
            "customer_id": customer_id,
            "agent_id": agent_id,
            "status": status[:50],
            "offer_amount": offer or 0,
            "notes": (m.get("notes") or "")[:4000],
            "external_id": external_id[:64],
        }
        # exact: same property+customer+status not deleted
        existing = Deal.query.filter_by(
            property_id=property_id,
            customer_id=customer_id,
            status=status,
            is_deleted=False,
        ).first()
        if existing:
            return RowClassification(
                "exact_duplicate",
                "deal_composite",
                f"Matches deal #{existing.id}",
                match_key=f"{property_id}:{customer_id}:{status}",
                payload=payload,
                existing_id=existing.id,
            )
        return RowClassification(
            "valid",
            "",
            "OK",
            match_key=f"{property_id}:{customer_id}:{status}",
            payload=payload,
        )

    def run_preview(self, batch: ImportBatch) -> Dict[str, int]:
        if not batch.temp_path or not Path(batch.temp_path).is_file():
            raise ValueError("Source file no longer available; re-upload")
        data = Path(batch.temp_path).read_bytes()
        parsed = parse_csv_bytes(data)
        # clear prior row results
        ImportRowResult.query.filter_by(batch_id=batch.id).delete()
        counts = {
            "valid": 0,
            "invalid": 0,
            "exact_duplicate": 0,
            "possible_duplicate": 0,
        }
        for idx, raw in enumerate(parsed.rows, start=1):
            cl = self.validate_and_classify_row(batch, idx, raw)
            counts[cl.outcome] = counts.get(cl.outcome, 0) + 1
            db.session.add(
                ImportRowResult(
                    batch_id=batch.id,
                    row_number=idx,
                    outcome=cl.outcome,
                    error_codes=cl.error_codes or "",
                    diagnostic=(cl.diagnostic or "")[:500],
                    match_key=(cl.match_key or "")[:255],
                    created_record_id=None,
                    payload_json=json.dumps(cl.payload or {}),
                    decision="skip" if cl.outcome == "exact_duplicate" else "",
                )
            )
        batch.valid_rows = counts.get("valid", 0)
        batch.invalid_rows = counts.get("invalid", 0)
        batch.duplicate_rows = counts.get("exact_duplicate", 0)
        batch.possible_duplicate_rows = counts.get("possible_duplicate", 0)
        batch.total_rows = sum(counts.values())
        batch.status = "previewed"
        db.session.commit()
        log_event(
            "import_validation_completed",
            component="import",
            batch_id=batch.id,
            valid=batch.valid_rows,
            invalid=batch.invalid_rows,
            duplicates=batch.duplicate_rows,
        )
        return counts

    def set_row_decision(
        self, batch: ImportBatch, row_id: int, decision: str, actor: str
    ) -> None:
        row = ImportRowResult.query.filter_by(id=row_id, batch_id=batch.id).first()
        if not row:
            raise ValueError("Row not found")
        if row.outcome not in ("possible_duplicate", "exact_duplicate", "valid"):
            raise ValueError("Decision not applicable")
        decision = (decision or "").strip().lower()
        if decision not in ("skip", "import"):
            raise ValueError("Invalid decision")
        if row.outcome == "exact_duplicate" and decision == "import":
            # create-only mode: never update; force skip
            decision = "skip"
        row.decision = decision
        row.decision_by = (actor or "")[:120]
        row.decision_at = _utcnow_naive()
        db.session.commit()
        log_event(
            "import_duplicate_decision",
            component="import",
            batch_id=batch.id,
            row_id=row_id,
            decision=decision,
        )

    def execute(self, batch: ImportBatch, *, skip_invalid: bool = False) -> ImportBatch:
        if batch.status not in ("previewed", "reviewing", "failed"):
            if batch.status == "completed":
                raise ValueError("Batch already completed")
        rows = (
            ImportRowResult.query.filter_by(batch_id=batch.id)
            .order_by(ImportRowResult.row_number)
            .all()
        )
        if not rows:
            raise ValueError("Run preview first")
        if not skip_invalid and any(r.outcome == "invalid" for r in rows):
            raise ValueError("Invalid rows present; fix file or enable skip_invalid")

        batch.status = "executing"
        batch.started_at = _utcnow_naive()
        batch.failure_category = None
        db.session.commit()
        log_event("import_execution_started", component="import", batch_id=batch.id)

        imported = 0
        skipped = 0
        try:
            for row in rows:
                if row.outcome == "invalid":
                    skipped += 1
                    row.outcome = "skipped"
                    continue
                if row.outcome == "exact_duplicate":
                    skipped += 1
                    row.outcome = "skipped"
                    continue
                if row.outcome == "possible_duplicate":
                    if row.decision != "import":
                        skipped += 1
                        row.outcome = "skipped"
                        continue
                if row.outcome == "valid" and row.decision == "skip":
                    skipped += 1
                    row.outcome = "skipped"
                    continue
                # import
                payload = json.loads(row.payload_json or "{}")
                rec_id = self._insert_entity(batch.entity_type, payload)
                row.created_record_id = rec_id
                row.outcome = "imported"
                imported += 1

            batch.imported_rows = imported
            batch.skipped_rows = skipped
            batch.status = "completed"
            batch.completed_at = _utcnow_naive()
            cleanup_temp(batch.temp_path)
            batch.temp_path = ""
            db.session.commit()
            record_business_counter(
                "crm_mutations_total", domain="import", outcome="ok"
            )
            log_event(
                "import_execution_completed",
                component="import",
                batch_id=batch.id,
                imported=imported,
                skipped=skipped,
            )
        except Exception as e:
            db.session.rollback()
            batch = db.session.get(ImportBatch, batch.id)
            batch.status = "failed"
            batch.failure_category = "internal"
            batch.completed_at = _utcnow_naive()
            db.session.commit()
            log_event(
                "import_execution_failed",
                component="import",
                batch_id=batch.id,
                error_category="internal",
            )
            raise ValueError(f"Import failed and was rolled back: {type(e).__name__}") from e
        return batch

    def _insert_entity(self, entity_type: str, payload: Dict[str, Any]) -> int:
        if entity_type == "customer":
            c = Customer(
                name=payload["name"],
                email=payload["email"],
                phone=payload["phone"],
                budget_min=payload.get("budget_min") or 0,
                budget_max=payload.get("budget_max") or 0,
                preferred_bedrooms=payload.get("preferred_bedrooms") or 0,
                preferred_bathrooms=payload.get("preferred_bathrooms") or 0,
                preferred_type=payload.get("preferred_type") or "",
                location_preference=payload.get("location_preference") or "",
                status=payload.get("status") or "active",
                customer_type=payload.get("customer_type") or "buyer",
                preferences=payload.get("preferences") or "",
            )
            db.session.add(c)
            db.session.flush()
            return c.id
        if entity_type == "property":
            p = Property(
                title=payload["title"],
                address=payload["address"],
                property_type=payload["property_type"],
                price=payload.get("price") or 0,
                bedrooms=payload.get("bedrooms") or 0,
                bathrooms=payload.get("bathrooms") or 0,
                square_feet=payload.get("square_feet") or 0,
                description=payload.get("description") or "",
                status=payload.get("status") or "active",
                listing_type=payload.get("listing_type") or "sale",
                neighborhood=payload.get("neighborhood") or "",
                source="import",
            )
            if payload.get("agent_id"):
                p.agent_id = payload["agent_id"]
            if payload.get("file_code"):
                p.file_code = payload["file_code"]
            if payload.get("year_built") is not None:
                p.year_built = payload["year_built"]
            db.session.add(p)
            db.session.flush()
            return p.id
        if entity_type == "deal":
            d = Deal(
                property_id=payload["property_id"],
                customer_id=payload["customer_id"],
                agent_id=payload.get("agent_id"),
                status=payload.get("status") or "prospecting",
                offer_amount=payload.get("offer_amount") or 0,
                notes=payload.get("notes") or "",
            )
            db.session.add(d)
            db.session.flush()
            return d.id
        raise ValueError("Unknown entity")

    def preview_rollback(self, batch: ImportBatch) -> Dict[str, Any]:
        rows = ImportRowResult.query.filter_by(
            batch_id=batch.id, outcome="imported"
        ).all()
        eligible = []
        blocked = []
        for row in rows:
            if not row.created_record_id:
                continue
            ok, reason = self._rollback_eligible(batch.entity_type, row.created_record_id)
            if ok:
                eligible.append(row.created_record_id)
            else:
                blocked.append({"id": row.created_record_id, "reason": reason})
        return {
            "eligible_count": len(eligible),
            "blocked_count": len(blocked),
            "eligible_ids": eligible,
            "blocked": blocked,
        }

    def _rollback_eligible(self, entity_type: str, record_id: int) -> Tuple[bool, str]:
        if entity_type == "customer":
            c = db.session.get(Customer, record_id)
            if not c or c.is_deleted:
                return False, "missing"
            if c.deals:
                return False, "has_deals"
            return True, ""
        if entity_type == "property":
            p = db.session.get(Property, record_id)
            if not p or getattr(p, "is_deleted", False):
                return False, "missing"
            if p.deals:
                return False, "has_deals"
            return True, ""
        if entity_type == "deal":
            d = db.session.get(Deal, record_id)
            if not d or d.is_deleted:
                return False, "missing"
            return True, ""
        return False, "unknown"

    def execute_rollback(self, batch: ImportBatch, actor: str) -> Dict[str, Any]:
        if batch.rollback_status == "rolled_back":
            return {"status": "already_rolled_back", "deleted": 0, "blocked": 0}
        if batch.status not in ("completed", "failed") and batch.rollback_status == "none":
            # Only completed imports are rollable; allow partial re-run states.
            if batch.imported_rows <= 0 and batch.status != "completed":
                return {
                    "status": "not_rollable",
                    "deleted": 0,
                    "blocked": 0,
                    "rollback_status": batch.rollback_status,
                }
        preview = self.preview_rollback(batch)
        deleted = 0
        for rid in preview["eligible_ids"]:
            ok, _ = self._rollback_eligible(batch.entity_type, rid)
            if not ok:
                continue
            if batch.entity_type == "customer":
                c = db.session.get(Customer, rid)
                if c:
                    c.is_deleted = True
                    c.deleted_at = _utcnow_naive()
            elif batch.entity_type == "property":
                p = db.session.get(Property, rid)
                if p:
                    p.is_deleted = True
                    p.deleted_at = _utcnow_naive()
            elif batch.entity_type == "deal":
                d = db.session.get(Deal, rid)
                if d:
                    d.is_deleted = True
                    d.deleted_at = _utcnow_naive()
            row = ImportRowResult.query.filter_by(
                batch_id=batch.id, created_record_id=rid
            ).first()
            if row:
                row.outcome = "rolled_back"
            deleted += 1
        if preview["blocked_count"] and deleted:
            batch.rollback_status = "rollback_partial"
        elif deleted and not preview["blocked_count"]:
            batch.rollback_status = "rolled_back"
        elif preview["blocked_count"] and not deleted:
            batch.rollback_status = "rollback_blocked"
        db.session.commit()
        log_event(
            "import_rollback_completed",
            component="import",
            batch_id=batch.id,
            deleted=deleted,
            blocked=preview["blocked_count"],
        )
        return {
            "deleted": deleted,
            "blocked": preview["blocked_count"],
            "rollback_status": batch.rollback_status,
        }


import_service = ImportService()
