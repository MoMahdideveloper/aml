"""CSV import UI and API (Track A)."""

from __future__ import annotations

import json
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database import db
from services.import_parser import ImportParseError, parse_csv_bytes, write_safe_csv
from services.import_service import ENTITY_FIELDS, import_service
from sqlalchemy_models import ImportBatch, ImportRowResult
from utils.execution_tracer import log_execution

bp = Blueprint("imports", __name__, url_prefix="/imports")

ALLOWED_ROLES = {"agent", "admin"}


def _require_import_user():
    uid = session.get("user_id")
    role = (session.get("user_role") or "agent").lower()
    if not uid:
        return None, redirect(url_for("auth.login"))
    if role not in ALLOWED_ROLES:
        flash("You do not have permission to import data.", "error")
        return None, redirect(url_for("main.dashboard"))
    return uid, None


def _get_owned_batch(batch_id: int, uid: int) -> ImportBatch:
    batch = db.session.get(ImportBatch, batch_id)
    if not batch:
        abort(404)
    # Object isolation: only uploader (or admin role) may access
    role = (session.get("user_role") or "").lower()
    if batch.uploader_id and batch.uploader_id != uid and role != "admin":
        abort(403)
    return batch


@bp.route("/", methods=["GET"])
@log_execution
def import_index():
    uid, denied = _require_import_user()
    if denied:
        return denied
    batches = (
        ImportBatch.query.filter_by(uploader_id=uid)
        .order_by(ImportBatch.id.desc())
        .limit(50)
        .all()
    )
    return render_template("imports/index.html", batches=batches)


@bp.route("/upload", methods=["GET", "POST"])
@log_execution
def upload():
    uid, denied = _require_import_user()
    if denied:
        return denied
    if request.method == "GET":
        return render_template("imports/upload.html")

    entity = (request.form.get("entity_type") or "").strip().lower()
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose a CSV file.", "error")
        return redirect(url_for("imports.upload"))
    raw = f.read()
    try:
        batch = import_service.create_batch_from_upload(
            entity_type=entity,
            filename=f.filename,
            data=raw,
            uploader_id=uid,
            uploader_label=session.get("user_name") or session.get("user_role") or "user",
        )
    except ImportParseError as e:
        flash(f"Upload rejected: {e.message}", "error")
        return redirect(url_for("imports.upload"))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("imports.upload"))

    flash(f"Uploaded {batch.total_rows} rows. Map columns next.", "success")
    return redirect(url_for("imports.map_columns", batch_id=batch.id))


@bp.route("/<int:batch_id>/map", methods=["GET", "POST"])
@log_execution
def map_columns(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)

    headers = []
    if batch.temp_path and Path(batch.temp_path).is_file():
        try:
            parsed = parse_csv_bytes(Path(batch.temp_path).read_bytes())
            headers = parsed.headers
        except ImportParseError as e:
            flash(e.message, "error")

    fields = ENTITY_FIELDS.get(batch.entity_type, [])
    if request.method == "POST":
        mapping = {}
        for field in fields:
            src = (request.form.get(f"map_{field}") or "").strip()
            if src:
                mapping[field] = src
        try:
            import_service.save_mapping(batch, mapping)
            import_service.run_preview(batch)
            flash("Preview ready.", "success")
            return redirect(url_for("imports.preview", batch_id=batch.id))
        except ValueError as e:
            flash(str(e), "error")

    current = json.loads(batch.mapping_json or "{}")
    return render_template(
        "imports/map.html",
        batch=batch,
        headers=headers,
        fields=fields,
        current=current,
    )


@bp.route("/<int:batch_id>/preview", methods=["GET"])
@log_execution
def preview(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)
    rows = (
        ImportRowResult.query.filter_by(batch_id=batch.id)
        .order_by(ImportRowResult.row_number)
        .limit(50)
        .all()
    )
    return render_template("imports/preview.html", batch=batch, rows=rows)


@bp.route("/<int:batch_id>/duplicates", methods=["GET", "POST"])
@log_execution
def duplicates(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)
    if request.method == "POST":
        # bulk skip exact
        if request.form.get("action") == "skip_all_exact":
            for row in ImportRowResult.query.filter_by(
                batch_id=batch.id, outcome="exact_duplicate"
            ):
                row.decision = "skip"
            db.session.commit()
            flash("Exact duplicates marked skip.", "success")
        else:
            for key, val in request.form.items():
                if key.startswith("decision_"):
                    rid = int(key.split("_", 1)[1])
                    try:
                        import_service.set_row_decision(
                            batch,
                            rid,
                            val,
                            session.get("user_name") or "user",
                        )
                    except ValueError:
                        pass
            flash("Decisions saved.", "success")
        batch.status = "reviewing"
        db.session.commit()
        return redirect(url_for("imports.duplicates", batch_id=batch.id))

    rows = (
        ImportRowResult.query.filter(
            ImportRowResult.batch_id == batch.id,
            ImportRowResult.outcome.in_(
                ("exact_duplicate", "possible_duplicate")
            ),
        )
        .order_by(ImportRowResult.row_number)
        .all()
    )
    return render_template("imports/duplicates.html", batch=batch, rows=rows)


@bp.route("/<int:batch_id>/execute", methods=["POST"])
@log_execution
def execute(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)
    skip_invalid = request.form.get("skip_invalid") == "1"
    try:
        import_service.execute(batch, skip_invalid=skip_invalid)
        flash(
            f"Import complete: {batch.imported_rows} imported, {batch.skipped_rows} skipped.",
            "success",
        )
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("imports.results", batch_id=batch.id))


@bp.route("/<int:batch_id>/results", methods=["GET"])
@log_execution
def results(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)
    rows = (
        ImportRowResult.query.filter_by(batch_id=batch.id)
        .order_by(ImportRowResult.row_number)
        .limit(100)
        .all()
    )
    return render_template("imports/results.html", batch=batch, rows=rows)


@bp.route("/<int:batch_id>/errors.csv", methods=["GET"])
@log_execution
def export_errors(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)
    rows = (
        ImportRowResult.query.filter(
            ImportRowResult.batch_id == batch.id,
            ImportRowResult.outcome.in_(("invalid", "failed")),
        )
        .order_by(ImportRowResult.row_number)
        .all()
    )
    data_rows = [
        [r.row_number, r.outcome, r.error_codes, r.diagnostic] for r in rows
    ]
    csv_text = write_safe_csv(
        ["row_number", "outcome", "error_codes", "diagnostic"], data_rows
    )
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=import_{batch.id}_errors.csv"
        },
    )


@bp.route("/<int:batch_id>/rollback", methods=["GET", "POST"])
@log_execution
def rollback(batch_id: int):
    uid, denied = _require_import_user()
    if denied:
        return denied
    batch = _get_owned_batch(batch_id, uid)
    preview = import_service.preview_rollback(batch)
    if request.method == "POST":
        if request.form.get("confirm") != "yes":
            flash("Confirmation required.", "error")
            return redirect(url_for("imports.rollback", batch_id=batch.id))
        result = import_service.execute_rollback(
            batch, session.get("user_name") or "user"
        )
        flash(
            f"Rollback: deleted={result.get('deleted')} blocked={result.get('blocked')}",
            "success",
        )
        return redirect(url_for("imports.results", batch_id=batch.id))
    return render_template("imports/rollback.html", batch=batch, preview=preview)
