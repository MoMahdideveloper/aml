"""Local document storage adapter tests (TDD)."""

import io
import os
from pathlib import Path

import pytest

from services.document_storage import DocumentStorageError, LocalDocumentStorage


@pytest.fixture()
def storage(tmp_path):
    root = tmp_path / "docs"
    return LocalDocumentStorage(str(root))


def test_store_and_open_roundtrip(storage):
    key = storage.generate_key("pdf")
    data = b"%PDF-1.4 synthetic test file"
    storage.store(io.BytesIO(data), key)
    assert storage.exists(key)
    assert storage.size(key) == len(data)
    with storage.open(key) as f:
        assert f.read() == data


def test_path_traversal_rejected(storage):
    with pytest.raises(DocumentStorageError):
        storage.store(io.BytesIO(b"x"), "../../../etc/passwd")
    with pytest.raises(DocumentStorageError):
        storage.open("..\\windows\\system32")


def test_same_filename_no_collision(storage):
    k1 = storage.generate_key("pdf")
    k2 = storage.generate_key("pdf")
    assert k1 != k2
    storage.store(io.BytesIO(b"a"), k1)
    storage.store(io.BytesIO(b"b"), k2)
    with storage.open(k1) as f:
        assert f.read() == b"a"
    with storage.open(k2) as f:
        assert f.read() == b"b"


def test_partial_write_cleanup_on_failure(storage, monkeypatch):
    key = storage.generate_key("bin")

    class Boom(io.BytesIO):
        def read(self, n=-1):
            raise OSError("disk full")

    with pytest.raises(DocumentStorageError):
        storage.store(Boom(b"partial"), key)
    assert not storage.exists(key)


def test_archive_moves_out_of_available(storage):
    key = storage.generate_key("txt")
    storage.store(io.BytesIO(b"hello"), key)
    arch = storage.archive(key)
    assert not storage.exists(key, area="available")
    assert storage.exists(arch, area="archived")
