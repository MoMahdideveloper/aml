"""Private document storage — never under static/."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import BinaryIO, Optional


class DocumentStorageError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class LocalDocumentStorage:
    """Filesystem adapter with opaque keys and path-traversal guards."""

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.available = self.root / "available"
        self.quarantine = self.root / "quarantine"
        self.archived = self.root / "archived"
        self.tmp = self.root / "tmp"
        for d in (self.available, self.quarantine, self.archived, self.tmp):
            d.mkdir(parents=True, exist_ok=True)

    def generate_key(self, ext_hint: str = "bin") -> str:
        ext = "".join(c for c in (ext_hint or "bin").lower() if c.isalnum())[:8] or "bin"
        return f"{uuid.uuid4().hex}.{ext}"

    def _resolve(self, key: str, base: Optional[Path] = None) -> Path:
        if not key or ".." in key or key.startswith(("/", "\\")) or ":" in key:
            raise DocumentStorageError("bad_key", "Invalid storage key")
        # only basename-like keys
        if "/" in key or "\\" in key:
            raise DocumentStorageError("bad_key", "Invalid storage key")
        base = base or self.available
        path = (base / key).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise DocumentStorageError("path_escape", "Path escapes storage root") from None
        return path

    def store(self, stream: BinaryIO, generated_key: str, *, target: str = "available") -> str:
        bases = {
            "available": self.available,
            "quarantine": self.quarantine,
            "archived": self.archived,
        }
        if target not in bases:
            raise DocumentStorageError("bad_target", "Invalid target")
        dest = self._resolve(generated_key, bases[target])
        tmp_fd, tmp_name = tempfile.mkstemp(dir=str(self.tmp), prefix="up_")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(tmp_fd, "wb") as out:
                while True:
                    chunk = stream.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            os.replace(str(tmp_path), str(dest))
            return generated_key
        except DocumentStorageError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise DocumentStorageError("store_failed", "Storage write failed") from e

    def open(self, key: str, *, area: str = "available"):
        bases = {
            "available": self.available,
            "quarantine": self.quarantine,
            "archived": self.archived,
        }
        path = self._resolve(key, bases.get(area, self.available))
        if not path.is_file():
            # try other areas for open by key if area unknown
            for b in bases.values():
                p = self._resolve(key, b)
                if p.is_file():
                    return open(p, "rb")
            raise DocumentStorageError("missing", "Object not found")
        return open(path, "rb")

    def exists(self, key: str, *, area: Optional[str] = None) -> bool:
        areas = (
            [area]
            if area
            else ["available", "quarantine", "archived"]
        )
        bases = {
            "available": self.available,
            "quarantine": self.quarantine,
            "archived": self.archived,
        }
        for a in areas:
            if a not in bases:
                continue
            try:
                p = self._resolve(key, bases[a])
            except DocumentStorageError:
                continue
            if p.is_file():
                return True
        return False

    def size(self, key: str) -> int:
        for area, base in (
            ("available", self.available),
            ("quarantine", self.quarantine),
            ("archived", self.archived),
        ):
            try:
                p = self._resolve(key, base)
            except DocumentStorageError:
                continue
            if p.is_file():
                return p.stat().st_size
        raise DocumentStorageError("missing", "Object not found")

    def move_to_quarantine(self, key: str) -> str:
        return self._move(key, self.available, self.quarantine)

    def archive(self, key: str) -> str:
        # may be in available
        src_area = None
        for name, base in (
            ("available", self.available),
            ("quarantine", self.quarantine),
        ):
            p = self._resolve(key, base)
            if p.is_file():
                src_area = base
                break
        if src_area is None:
            raise DocumentStorageError("missing", "Object not found")
        return self._move(key, src_area, self.archived)

    def _move(self, key: str, src_base: Path, dest_base: Path) -> str:
        src = self._resolve(key, src_base)
        dest = self._resolve(key, dest_base)
        if not src.is_file():
            raise DocumentStorageError("missing", "Object not found")
        os.replace(str(src), str(dest))
        return key

    def delete(self, key: str) -> None:
        """Reserved for controlled maintenance only."""
        for base in (self.available, self.quarantine, self.archived):
            p = self._resolve(key, base)
            if p.is_file():
                p.unlink()
                return
        raise DocumentStorageError("missing", "Object not found")


def get_document_storage(app=None) -> LocalDocumentStorage:
    """Resolve storage root from app config / env."""
    import os
    from flask import current_app, has_app_context

    root = os.environ.get("DOCUMENT_STORAGE_ROOT")
    if not root and has_app_context():
        root = current_app.config.get("DOCUMENT_STORAGE_ROOT")
    if not root and has_app_context():
        root = os.path.join(current_app.instance_path, "document_store")
    if not root:
        root = os.path.join(os.getcwd(), "instance", "document_store")
    # Production guard
    env = os.environ.get("FLASK_ENV", "")
    if env == "production" and not os.environ.get("DOCUMENT_STORAGE_ROOT"):
        raise DocumentStorageError(
            "config",
            "DOCUMENT_STORAGE_ROOT must be set in production",
        )
    return LocalDocumentStorage(root)
