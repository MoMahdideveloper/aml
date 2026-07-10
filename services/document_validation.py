"""Content-type detection and size bounds for secure uploads."""

from __future__ import annotations

import hashlib
import io
import re
from typing import BinaryIO, Dict, Optional, Tuple

CATEGORIES = frozenset(
    {
        "identity",
        "mandate",
        "contract",
        "disclosure",
        "property_document",
        "offer",
        "correspondence",
        "other",
    }
)
OWNER_TYPES = frozenset({"customer", "property", "deal", "agent"})
STATUSES = frozenset(
    {"pending_scan", "available", "quarantined", "archived", "failed"}
)

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_PER_OWNER = 50
MAX_DISPLAY_NAME = 200

ALLOWED_MEDIA = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "text/plain": "txt",
}


class DocumentValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def size_band(n: int) -> str:
    if n < 100_000:
        return "lt_100kb"
    if n < 1_000_000:
        return "100kb_1mb"
    if n < 5_000_000:
        return "1_5mb"
    if n < 10_000_000:
        return "5_10mb"
    return "gt_10mb"


def sanitize_display_filename(name: str) -> str:
    name = (name or "document").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f]", "", name)
    name = re.sub(r'[<>:"|?*]', "_", name)
    name = name.strip() or "document"
    return name[:255]


def detect_media_type(header: bytes) -> Optional[str]:
    if header.startswith(b"%PDF"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    # reject HTML/SVG early
    low = header[:200].lstrip().lower()
    if low.startswith(b"<!doctype") or low.startswith(b"<html") or low.startswith(b"<svg"):
        return None
    # plain text heuristic: no NUL, mostly printable
    sample = header[:4096]
    if b"\x00" in sample:
        return None
    try:
        sample.decode("utf-8")
        return "text/plain"
    except UnicodeDecodeError:
        return None


def stream_hash_and_cap(
    stream: BinaryIO, max_bytes: int = MAX_BYTES
) -> Tuple[bytes, str, int]:
    """Read stream with cap; return (data, sha256_hex, size). For small caps only.

    Prefer streaming to temp file in service for large files; tests use this.
    """
    h = hashlib.sha256()
    chunks = []
    total = 0
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise DocumentValidationError("too_large", f"File exceeds {max_bytes} bytes")
        h.update(chunk)
        chunks.append(chunk)
    if total == 0:
        raise DocumentValidationError("empty", "File is empty")
    data = b"".join(chunks)
    return data, h.hexdigest(), total


def validate_content(data: bytes, media_type: str) -> None:
    if media_type == "application/pdf":
        if not data.startswith(b"%PDF"):
            raise DocumentValidationError("bad_pdf", "Invalid PDF")
        # reject obvious JS embedding for basic safety (heuristic)
        if b"/JavaScript" in data[:50000] or b"/JS" in data[:50000]:
            raise DocumentValidationError("unsafe_pdf", "PDF contains script")
        return
    if media_type == "text/plain":
        if len(data) > MAX_TEXT_BYTES:
            raise DocumentValidationError("too_large", "Text too large")
        if b"\x00" in data:
            raise DocumentValidationError("binary_text", "Text contains binary")
        data.decode("utf-8")
        return
    if media_type in ("image/jpeg", "image/png", "image/webp"):
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(data))
            img.verify()
            img = Image.open(io.BytesIO(data))
            w, h = img.size
            if w * h > MAX_PIXELS:
                raise DocumentValidationError("image_bomb", "Image too large")
        except DocumentValidationError:
            raise
        except Exception as e:
            raise DocumentValidationError("bad_image", "Invalid image") from e
        return
    raise DocumentValidationError("unsupported", "Unsupported media type")


# EICAR-like marker for fake scanner
EICAR_MARKER = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"


def fake_scan(data: bytes) -> Tuple[str, str]:
    """Deterministic dev scanner. Returns (result, engine)."""
    if EICAR_MARKER in data:
        return "infected", "fake_scanner"
    return "clean", "fake_scanner"
