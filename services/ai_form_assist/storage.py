"""Private audit media storage (never under static/)."""

from __future__ import annotations

import hashlib
import os
import secrets
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# Simple magic-byte sniffing (not full libmagic)
_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # webp/wav share RIFF — refined below
    b"ID3": "audio/mpeg",
    b"\x1aE\xdf\xa3": "audio/webm",  # EBML
}

MAX_BYTES_DEFAULT = 8 * 1024 * 1024  # 8 MiB
MAX_FILES_DEFAULT = 8


class StorageError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _default_root() -> Path:
    env = (os.environ.get("AI_FORM_AUDIT_STORAGE_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    # Default: instance/ai_form_audit under project (not static/)
    return (Path.cwd() / "instance" / "ai_form_audit").resolve()


class PrivateAuditStorage:
    """Local filesystem backend for extraction audit media."""

    def __init__(
        self,
        root: Optional[Path] = None,
        *,
        max_bytes: int = MAX_BYTES_DEFAULT,
        max_files: int = MAX_FILES_DEFAULT,
    ) -> None:
        self.root = (root or _default_root()).resolve()
        self.max_bytes = max_bytes
        self.max_files = max_files
        self._assert_not_static(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _assert_not_static(path: Path) -> None:
        parts = {p.lower() for p in path.parts}
        if "static" in parts:
            raise StorageError(
                "static_forbidden",
                "AI form audit storage root must not be under static/",
            )

    def _confine(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise StorageError("path_escape", "Path escapes storage root") from exc
        return resolved

    def sniff_mime(self, data: bytes) -> Optional[str]:
        if not data:
            return None
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
            return "image/webp"
        if data.startswith(b"ID3") or (len(data) > 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
            return "audio/mpeg"
        if data.startswith(b"\x1aE\xdf\xa3"):
            return "audio/webm"
        if data.startswith(b"OggS"):
            return "audio/ogg"
        return None

    def store(
        self,
        data: bytes,
        *,
        declared_mime: str = "",
        original_filename: str = "",
    ) -> dict:
        if not data:
            raise StorageError("empty", "Empty media payload")
        if len(data) > self.max_bytes:
            raise StorageError("too_large", f"Exceeds max_bytes={self.max_bytes}")

        sniffed = self.sniff_mime(data)
        mime = sniffed or (declared_mime or "application/octet-stream")
        if sniffed and declared_mime and not declared_mime.startswith(sniffed.split("/")[0]):
            # Allow if declared is empty; soft-check family only
            pass

        token = secrets.token_hex(16)
        # Server-generated name only — never use original filename for path
        rel = f"{token[:2]}/{token}.bin"
        dest = self._confine(self.root / rel)
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        fd, tmp_name = tempfile.mkstemp(dir=str(dest.parent), prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, dest)
        finally:
            if os.path.exists(tmp_name):
                try:
                    os.remove(tmp_name)
                except OSError:
                    pass

        digest = hashlib.sha256(data).hexdigest()
        return {
            "storage_key": rel.replace("\\", "/"),
            "sha256": digest,
            "byte_size": len(data),
            "mime_type": mime,
            # original filename retained for audit metadata only, not path
            "original_filename": (original_filename or "")[:200],
        }

    def delete(self, storage_key: str) -> bool:
        if not storage_key or ".." in storage_key or storage_key.startswith(("/", "\\")):
            raise StorageError("bad_key", "Invalid storage key")
        path = self._confine(self.root / storage_key)
        if path.is_file():
            path.unlink()
            return True
        return False

    def resolve_path(self, storage_key: str) -> Path:
        if not storage_key or ".." in storage_key:
            raise StorageError("bad_key", "Invalid storage key")
        return self._confine(self.root / storage_key)
