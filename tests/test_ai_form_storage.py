"""Private audit media storage tests."""

import pytest

from services.ai_form_assist.storage import PrivateAuditStorage, StorageError


def test_store_and_delete_jpeg(tmp_path):
    store = PrivateAuditStorage(root=tmp_path / "audit")
    data = b"\xff\xd8\xff" + b"\x00" * 100
    meta = store.store(data, declared_mime="image/jpeg", original_filename="evil/../../x.jpg")
    assert meta["byte_size"] == len(data)
    assert meta["sha256"]
    assert ".." not in meta["storage_key"]
    assert "evil" not in meta["storage_key"]
    path = store.resolve_path(meta["storage_key"])
    assert path.is_file()
    assert store.delete(meta["storage_key"]) is True


def test_rejects_static_root(tmp_path):
    bad = tmp_path / "static" / "uploads"
    bad.mkdir(parents=True)
    with pytest.raises(StorageError) as ei:
        PrivateAuditStorage(root=bad)
    assert ei.value.code == "static_forbidden"


def test_path_escape_rejected(tmp_path):
    store = PrivateAuditStorage(root=tmp_path / "audit")
    with pytest.raises(StorageError):
        store.delete("../etc/passwd")


def test_too_large(tmp_path):
    store = PrivateAuditStorage(root=tmp_path / "audit", max_bytes=10)
    with pytest.raises(StorageError) as ei:
        store.store(b"\xff\xd8\xff" + b"x" * 20)
    assert ei.value.code == "too_large"


def test_empty_rejected(tmp_path):
    store = PrivateAuditStorage(root=tmp_path / "audit")
    with pytest.raises(StorageError) as ei:
        store.store(b"")
    assert ei.value.code == "empty"
