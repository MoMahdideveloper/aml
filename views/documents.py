"""Secure document routes — authz + stream download, never static paths."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask import Response, stream_with_context

from services.document_service import DocumentServiceError, document_service
from services.document_validation import CATEGORIES
from utils.execution_tracer import log_execution
from utils.observability import log_event

bp = Blueprint("documents", __name__)

ALLOWED_ROLES = frozenset({"agent", "admin"})
ENTITY_PREFIX = {
    "customers": "customer",
    "properties": "property",
    "deals": "deal",
    "agents": "agent",
}


def _require_user():
    uid = session.get("user_id")
    role = (session.get("user_role") or "agent").lower()
    if not uid:
        return None, None, redirect(url_for("auth.login"))
    if role not in ALLOWED_ROLES:
        flash("Permission denied.", "error")
        return None, None, redirect(url_for("main.dashboard"))
    return uid, role, None


def _owner_list_url(owner_type: str, owner_id: int) -> str:
    try:
        if owner_type == "deal":
            return url_for("deals.deals") + f"?highlight={owner_id}"
        if owner_type == "customer":
            return url_for("customers.customer_360", customer_id=owner_id)
        if owner_type == "property":
            return url_for("properties.view_property", property_id=owner_id)
        if owner_type == "agent":
            return url_for("agents.agent_dashboard", agent_id=owner_id)
    except Exception:
        pass
    return url_for("main.dashboard")


@bp.route("/<entity>/<int:owner_id>/documents", methods=["GET", "POST"])
@log_execution
def entity_documents(entity: str, owner_id: int):
    uid, role, denied = _require_user()
    if denied:
        return denied
    owner_type = ENTITY_PREFIX.get(entity)
    if not owner_type:
        abort(404)

    if request.method == "POST":
        try:
            f = request.files.get("file")
            document_service.upload(
                owner_type=owner_type,
                owner_id=owner_id,
                file_storage=f,
                category=request.form.get("category") or "other",
                display_name=request.form.get("display_name") or "",
                actor_id=uid,
                actor_label=session.get("user_name") or "user",
                replace_group_id=request.form.get("replace_group_id") or None,
                force_duplicate=request.form.get("force_duplicate") == "1",
            )
            flash("Document uploaded.", "success")
        except DocumentServiceError as e:
            flash(e.message, "error")
            log_event(
                "document_upload_failed",
                component="documents",
                failure_category=e.code,
                owner_type=owner_type,
            )
        return redirect(
            url_for("documents.entity_documents", entity=entity, owner_id=owner_id)
        )

    try:
        docs = document_service.list_for_owner(owner_type, owner_id)
    except DocumentServiceError as e:
        flash(e.message, "error")
        return redirect(url_for("main.dashboard"))

    return render_template(
        "documents/list.html",
        documents=docs,
        owner_type=owner_type,
        owner_id=owner_id,
        entity=entity,
        categories=sorted(CATEGORIES),
        back_url=_owner_list_url(owner_type, owner_id),
    )


@bp.route("/documents/<int:document_id>/download")
@log_execution
def download(document_id: int):
    uid, role, denied = _require_user()
    if denied:
        return denied
    inline = request.args.get("inline") == "1"
    try:
        doc, fh, disposition = document_service.prepare_download(
            document_id,
            actor_id=uid,
            actor_label=session.get("user_name") or "user",
            inline=inline,
        )
    except DocumentServiceError as e:
        log_event(
            "document_download_denied",
            component="documents",
            failure_category=e.code,
        )
        abort(e.http)

    def generate():
        try:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            fh.close()

    # sanitize filename for header
    name = "".join(
        c if c.isalnum() or c in "._- " else "_"
        for c in (doc.display_name or "document")
    )[:180]
    headers = {
        "Content-Disposition": f'{disposition}; filename="{name}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    }
    return Response(
        stream_with_context(generate()),
        mimetype=doc.media_type or "application/octet-stream",
        headers=headers,
    )


@bp.route("/documents/<int:document_id>/versions", methods=["POST"])
@log_execution
def new_version(document_id: int):
    uid, role, denied = _require_user()
    if denied:
        return denied
    try:
        base = document_service.get_for_actor(document_id)
        f = request.files.get("file")
        document_service.upload(
            owner_type=base.owner_type,
            owner_id=base.owner_id,
            file_storage=f,
            category=base.category,
            display_name=request.form.get("display_name") or base.display_name,
            actor_id=uid,
            actor_label=session.get("user_name") or "user",
            replace_group_id=base.document_group_id,
        )
        flash("New version uploaded.", "success")
        entity = {v: k for k, v in ENTITY_PREFIX.items()}[base.owner_type]
        return redirect(
            url_for(
                "documents.entity_documents",
                entity=entity,
                owner_id=base.owner_id,
            )
        )
    except DocumentServiceError as e:
        flash(e.message, "error")
        return redirect(request.referrer or url_for("main.dashboard"))


@bp.route("/documents/<int:document_id>/archive", methods=["POST"])
@log_execution
def archive(document_id: int):
    uid, role, denied = _require_user()
    if denied:
        return denied
    if request.form.get("confirm") != "yes":
        flash("Confirmation required.", "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    try:
        doc = document_service.archive(
            document_id, actor_id=uid, actor_label=session.get("user_name") or "user"
        )
        flash("Document archived.", "success")
        entity = {v: k for k, v in ENTITY_PREFIX.items()}[doc.owner_type]
        return redirect(
            url_for(
                "documents.entity_documents",
                entity=entity,
                owner_id=doc.owner_id,
            )
        )
    except DocumentServiceError as e:
        flash(e.message, "error")
        return redirect(request.referrer or url_for("main.dashboard"))
