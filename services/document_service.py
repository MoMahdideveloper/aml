"""Document upload/query/version/archive service."""

from __future__ import annotations

import hashlib
import io
import os
import uuid
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

from flask import g, has_request_context
from werkzeug.datastructures import FileStorage

from database import db
from services.document_storage import (
    DocumentStorageError,
    LocalDocumentStorage,
    get_document_storage,
)
from services.document_validation import (
    ALLOWED_MEDIA,
    CATEGORIES,
    MAX_BYTES,
    MAX_DISPLAY_NAME,
    MAX_PER_OWNER,
    OWNER_TYPES,
    detect_media_type,
    fake_scan,
    sanitize_display_filename,
    size_band,
    validate_content,
    DocumentValidationError,
)
from sqlalchemy_models import (
    Agent,
    Customer,
    Deal,
    Document,
    DocumentAuditLog,
    Property,
    _utcnow_naive,
)
from utils.observability import log_event, record_business_counter


class DocumentServiceError(ValueError):
    def __init__(self, code: str, message: str, http: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http = http


def _rid() -> str:
    if has_request_context():
        return str(getattr(g, "request_id", "") or "")[:64]
    return ""


def _audit(
    *,
    document_id: Optional[int],
    actor_id: Optional[int],
    actor_label: str,
    action: str,
    result: str,
    owner_type: str = "",
    category: str = "",
    byte_size: int = 0,
) -> None:
    db.session.add(
        DocumentAuditLog(
            document_id=document_id,
            actor_id=actor_id,
            actor_label=(actor_label or "")[:120],
            action=action[:40],
            result=result[:20],
            request_id=_rid(),
            owner_type=owner_type[:20],
            category=category[:40],
            size_band=size_band(byte_size),
        )
    )


class DocumentService:
    def __init__(self, storage: Optional[LocalDocumentStorage] = None):
        self.storage = storage

    def _store(self) -> LocalDocumentStorage:
        return self.storage or get_document_storage()

    def assert_owner_exists(self, owner_type: str, owner_id: int) -> None:
        if owner_type not in OWNER_TYPES:
            raise DocumentServiceError("bad_owner_type", "Invalid owner type", 400)
        model = {
            "customer": Customer,
            "property": Property,
            "deal": Deal,
            "agent": Agent,
        }[owner_type]
        obj = db.session.get(model, owner_id)
        if not obj or getattr(obj, "is_deleted", False):
            raise DocumentServiceError("owner_not_found", "Owner not found", 404)

    def count_active(self, owner_type: str, owner_id: int) -> int:
        return Document.query.filter(
            Document.owner_type == owner_type,
            Document.owner_id == owner_id,
            Document.status.in_(["pending_scan", "available", "quarantined"]),
            Document.is_latest.is_(True),
        ).count()

    def upload(
        self,
        *,
        owner_type: str,
        owner_id: int,
        file_storage: FileStorage,
        category: str,
        display_name: str = "",
        actor_id: Optional[int] = None,
        actor_label: str = "",
        replace_group_id: Optional[str] = None,
        force_duplicate: bool = False,
    ) -> Document:
        owner_type = (owner_type or "").strip().lower()
        category = (category or "").strip().lower()
        if category not in CATEGORIES:
            raise DocumentServiceError("bad_category", "Invalid category")
        self.assert_owner_exists(owner_type, owner_id)

        if self.count_active(owner_type, owner_id) >= MAX_PER_OWNER and not replace_group_id:
            raise DocumentServiceError("quota", f"Max {MAX_PER_OWNER} documents per owner")

        if not file_storage or not file_storage.filename:
            raise DocumentServiceError("no_file", "No file provided")

        # Stream to memory with cap (10MB policy — acceptable for bound)
        h = hashlib.sha256()
        chunks: List[bytes] = []
        total = 0
        stream = file_storage.stream
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise DocumentServiceError("too_large", f"Exceeds {MAX_BYTES} bytes")
            h.update(chunk)
            chunks.append(chunk)
        if total == 0:
            raise DocumentServiceError("empty", "Empty file")
        data = b"".join(chunks)
        digest = h.hexdigest()

        header = data[:16]
        media = detect_media_type(header if len(data) >= 16 else data)
        if not media or media not in ALLOWED_MEDIA:
            raise DocumentServiceError("unsupported_type", "File type not allowed")
        try:
            validate_content(data, media)
        except DocumentValidationError as e:
            raise DocumentServiceError(e.code, e.message) from e

        # Duplicate within owner (latest available)
        if not force_duplicate and not replace_group_id:
            dup = Document.query.filter(
                Document.owner_type == owner_type,
                Document.owner_id == owner_id,
                Document.sha256 == digest,
                Document.status == "available",
                Document.is_latest.is_(True),
            ).first()
            if dup:
                raise DocumentServiceError(
                    "duplicate",
                    f"Duplicate of document #{dup.id} (same checksum). Pass force to create separate.",
                    409,
                )

        ext = ALLOWED_MEDIA[media]
        store = self._store()
        key = store.generate_key(ext)
        orig = sanitize_display_filename(file_storage.filename)
        dname = (display_name or orig)[:MAX_DISPLAY_NAME]

        version = 1
        group_id = uuid.uuid4().hex[:32]
        if replace_group_id:
            latest = (
                Document.query.filter_by(
                    document_group_id=replace_group_id,
                    is_latest=True,
                    owner_type=owner_type,
                    owner_id=owner_id,
                )
                .first()
            )
            if not latest or latest.status not in ("available", "archived"):
                raise DocumentServiceError("bad_version", "Cannot version this document")
            version = latest.version + 1
            group_id = replace_group_id
            latest.is_latest = False

        doc = Document(
            owner_type=owner_type,
            owner_id=owner_id,
            category=category,
            display_name=dname,
            original_filename=orig,
            storage_key=key,
            media_type=media,
            byte_size=total,
            sha256=digest,
            status="pending_scan",
            version=version,
            document_group_id=group_id,
            is_latest=True,
            uploaded_by=actor_id,
            uploaded_by_label=(actor_label or "")[:120],
            uploaded_at=_utcnow_naive(),
        )
        db.session.add(doc)
        db.session.flush()

        # Scan before final placement
        result, engine = fake_scan(data)
        doc.scan_engine = engine
        doc.scan_result = result

        try:
            if result != "clean":
                store.store(io.BytesIO(data), key, target="quarantine")
                doc.status = "quarantined"
                _audit(
                    document_id=doc.id,
                    actor_id=actor_id,
                    actor_label=actor_label,
                    action="quarantine",
                    result="ok",
                    owner_type=owner_type,
                    category=category,
                    byte_size=total,
                )
            else:
                store.store(io.BytesIO(data), key, target="available")
                doc.status = "available"
                _audit(
                    document_id=doc.id,
                    actor_id=actor_id,
                    actor_label=actor_label,
                    action="upload",
                    result="ok",
                    owner_type=owner_type,
                    category=category,
                    byte_size=total,
                )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            try:
                store.delete(key)
            except Exception:
                pass
            raise DocumentServiceError("store_failed", "Upload storage failed") from e

        log_event(
            "document_upload_succeeded",
            component="documents",
            owner_type=owner_type,
            category=category,
            size_band=size_band(total),
            status=doc.status,
            # no filename/path/checksum
        )
        record_business_counter("crm_document_uploads", outcome=doc.status)
        return doc

    def list_for_owner(
        self,
        owner_type: str,
        owner_id: int,
        *,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        self.assert_owner_exists(owner_type, owner_id)
        q = Document.query.filter(
            Document.owner_type == owner_type,
            Document.owner_id == owner_id,
            Document.is_latest.is_(True),
        )
        if include_archived:
            q = q.filter(Document.status.in_(["available", "archived", "quarantined", "pending_scan"]))
        else:
            q = q.filter(Document.status.in_(["available", "pending_scan", "quarantined"]))
        return (
            q.order_by(Document.uploaded_at.desc(), Document.id.desc())
            .offset(max(0, offset))
            .limit(min(max(1, limit), 100))
            .all()
        )

    def get_for_actor(self, document_id: int) -> Document:
        doc = db.session.get(Document, document_id)
        if not doc:
            raise DocumentServiceError("not_found", "Document not found", 404)
        # ensure owner still exists
        try:
            self.assert_owner_exists(doc.owner_type, doc.owner_id)
        except DocumentServiceError:
            raise DocumentServiceError("not_found", "Document not found", 404) from None
        return doc

    def versions(self, document_id: int) -> List[Document]:
        doc = self.get_for_actor(document_id)
        return (
            Document.query.filter_by(document_group_id=doc.document_group_id)
            .order_by(Document.version.desc())
            .all()
        )

    def prepare_download(
        self, document_id: int, *, actor_id: Optional[int], actor_label: str, inline: bool = False
    ) -> Tuple[Document, Any, str]:
        doc = self.get_for_actor(document_id)
        if doc.status != "available":
            _audit(
                document_id=doc.id,
                actor_id=actor_id,
                actor_label=actor_label,
                action="download",
                result="denied",
                owner_type=doc.owner_type,
                category=doc.category,
                byte_size=doc.byte_size,
            )
            db.session.commit()
            raise DocumentServiceError("not_available", "Document not available for download", 403)
        store = self._store()
        try:
            fh = store.open(doc.storage_key, area="available")
        except DocumentStorageError:
            log_event(
                "document_storage_missing",
                component="documents",
                document_id=doc.id,
                owner_type=doc.owner_type,
            )
            raise DocumentServiceError("missing_object", "File missing from storage", 404)
        _audit(
            document_id=doc.id,
            actor_id=actor_id,
            actor_label=actor_label,
            action="download",
            result="ok",
            owner_type=doc.owner_type,
            category=doc.category,
            byte_size=doc.byte_size,
        )
        db.session.commit()
        log_event(
            "document_downloaded",
            component="documents",
            owner_type=doc.owner_type,
            category=doc.category,
            size_band=size_band(doc.byte_size),
        )
        disposition = "inline" if inline and doc.media_type.startswith(
            ("image/", "application/pdf")
        ) else "attachment"
        return doc, fh, disposition

    def archive(
        self, document_id: int, *, actor_id: Optional[int], actor_label: str
    ) -> Document:
        doc = self.get_for_actor(document_id)
        if doc.status not in ("available", "quarantined"):
            raise DocumentServiceError("bad_state", "Cannot archive in this status")
        store = self._store()
        try:
            store.archive(doc.storage_key)
        except DocumentStorageError as e:
            raise DocumentServiceError("storage", e.message) from e
        doc.status = "archived"
        doc.archived_at = _utcnow_naive()
        doc.archived_by = actor_id
        _audit(
            document_id=doc.id,
            actor_id=actor_id,
            actor_label=actor_label,
            action="archive",
            result="ok",
            owner_type=doc.owner_type,
            category=doc.category,
            byte_size=doc.byte_size,
        )
        db.session.commit()
        log_event(
            "document_archived",
            component="documents",
            owner_type=doc.owner_type,
            category=doc.category,
        )
        return doc


document_service = DocumentService()
