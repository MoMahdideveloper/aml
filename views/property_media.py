"""Property multi-image gallery upload / manage routes."""

from __future__ import annotations

import logging
import os
import uuid
from typing import List

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from database import db
from property_error_handlers import PropertyNotFoundError, get_property_with_related_data
from sqlalchemy_models import PropertyImage

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_FILES_PER_UPLOAD = 12


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _upload_folder() -> str:
    folder = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(folder, exist_ok=True)
    return folder


def _gallery_images(property_id: int) -> List[PropertyImage]:
    return (
        PropertyImage.query.filter_by(property_id=property_id)
        .order_by(PropertyImage.is_primary.desc(), PropertyImage.display_order.asc(), PropertyImage.id.asc())
        .all()
    )


def _unique_filename(original: str) -> str:
    base = secure_filename(original) or "image"
    name, ext = os.path.splitext(base)
    if not ext:
        ext = ".jpg"
    return f"{name[:40]}_{uuid.uuid4().hex[:10]}{ext.lower()}"


def _load_property(property_id: int):
    try:
        return get_property_with_related_data(property_id)
    except PropertyNotFoundError:
        return None
    except Exception:
        logging.exception("Failed loading property %s", property_id)
        return None


def property_media(property_id: int):
    """GET: media manager page. POST: multi-file upload."""
    property_obj = _load_property(property_id)
    if property_obj is None:
        flash("Property not found", "error")
        return redirect(url_for("properties.properties"))

    if request.method == "POST":
        return upload_property_media(property_id)

    images = _gallery_images(property_id)
    # Also surface legacy single image if not already in gallery
    legacy = getattr(property_obj, "image_filename", None)
    return render_template(
        "property_media.html",
        property=property_obj,
        images=images,
        legacy_image=legacy,
    )


def upload_property_media(property_id: int):
    """POST multi-file upload into property_images (+ optional primary cover)."""
    property_obj = _load_property(property_id)
    if property_obj is None:
        flash("Property not found", "error")
        return redirect(url_for("properties.properties"))

    files = request.files.getlist("images") or []
    # Support single field name too
    if not files and request.files.get("image"):
        files = [request.files.get("image")]

    files = [f for f in files if f and getattr(f, "filename", None)]
    if not files:
        flash("Choose at least one image to upload.", "error")
        return redirect(url_for("properties.property_media", property_id=property_id))

    if len(files) > MAX_FILES_PER_UPLOAD:
        flash(f"Upload up to {MAX_FILES_PER_UPLOAD} files at a time.", "error")
        return redirect(url_for("properties.property_media", property_id=property_id))

    existing = _gallery_images(property_id)
    next_order = (max((img.display_order for img in existing), default=-1) + 1)
    has_primary = any(img.is_primary for img in existing) or bool(getattr(property_obj, "image_filename", None))
    uploaded = 0
    folder = _upload_folder()

    try:
        for f in files:
            if not _allowed(f.filename):
                flash(f"Skipped unsupported file: {f.filename}", "error")
                continue
            filename = _unique_filename(f.filename)
            path = os.path.join(folder, filename)
            f.save(path)

            img = PropertyImage()
            img.property_id = property_id
            img.filename = filename
            img.caption = (request.form.get("caption") or "").strip() or None
            img.display_order = next_order
            img.is_primary = False
            next_order += 1

            if not has_primary:
                img.is_primary = True
                has_primary = True
                property_obj.image_filename = filename

            db.session.add(img)
            uploaded += 1

        db.session.commit()
        if uploaded:
            flash(f"Uploaded {uploaded} image{'s' if uploaded != 1 else ''}.", "success")
        else:
            flash("No valid images uploaded.", "error")
    except Exception as e:
        db.session.rollback()
        logging.exception("Media upload failed for property %s", property_id)
        flash(f"Upload failed: {e}", "error")

    # Prefer returning to media page; detail also works
    next_url = request.form.get("next") or url_for("properties.property_media", property_id=property_id)
    return redirect(next_url)


def set_primary_image(property_id: int, image_id: int):
    property_obj = _load_property(property_id)
    if property_obj is None:
        flash("Property not found", "error")
        return redirect(url_for("properties.properties"))

    img = PropertyImage.query.filter_by(id=image_id, property_id=property_id).first()
    if not img:
        flash("Image not found", "error")
        return redirect(url_for("properties.property_media", property_id=property_id))

    try:
        PropertyImage.query.filter_by(property_id=property_id).update({"is_primary": False})
        img.is_primary = True
        property_obj.image_filename = img.filename
        db.session.commit()
        flash("Cover image updated.", "success")
    except Exception as e:
        db.session.rollback()
        logging.exception("Set primary failed")
        flash(f"Could not set cover: {e}", "error")

    return redirect(request.referrer or url_for("properties.property_media", property_id=property_id))


def delete_property_image(property_id: int, image_id: int):
    property_obj = _load_property(property_id)
    if property_obj is None:
        flash("Property not found", "error")
        return redirect(url_for("properties.properties"))

    img = PropertyImage.query.filter_by(id=image_id, property_id=property_id).first()
    if not img:
        flash("Image not found", "error")
        return redirect(url_for("properties.property_media", property_id=property_id))

    try:
        was_primary = img.is_primary
        filename = img.filename
        db.session.delete(img)
        db.session.flush()

        if was_primary or property_obj.image_filename == filename:
            remaining = _gallery_images(property_id)
            if remaining:
                remaining[0].is_primary = True
                property_obj.image_filename = remaining[0].filename
            else:
                property_obj.image_filename = None

        db.session.commit()

        # Best-effort file delete
        try:
            path = os.path.join(_upload_folder(), filename)
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

        flash("Image removed.", "success")
    except Exception as e:
        db.session.rollback()
        logging.exception("Delete image failed")
        flash(f"Could not delete image: {e}", "error")

    return redirect(request.referrer or url_for("properties.property_media", property_id=property_id))
