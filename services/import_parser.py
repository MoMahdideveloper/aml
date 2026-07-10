"""Secure CSV parsing for Track A imports."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 500
MAX_COLUMNS = 40
MAX_FIELD_LEN = 4000


class ImportParseError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ParsedCSV:
    headers: List[str]
    rows: List[Dict[str, str]]
    file_hash: str
    raw_row_count: int


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sniff_is_text_csv(data: bytes) -> None:
    if not data:
        raise ImportParseError("empty", "File is empty")
    if len(data) > MAX_BYTES:
        raise ImportParseError("too_large", f"File exceeds {MAX_BYTES} bytes")
    # Reject obvious binary (NUL)
    if b"\x00" in data[:8192]:
        raise ImportParseError("binary", "Binary content is not allowed")
    # Magic: reject common non-CSV
    if data[:4] in (b"%PDF", b"PK\x03\x04", b"\x89PNG"):
        raise ImportParseError("not_csv", "Content is not CSV")


def decode_csv_bytes(data: bytes) -> str:
    sniff_is_text_csv(data)
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ImportParseError("encoding", "File must be UTF-8") from e


def normalize_header(h: str) -> str:
    return re.sub(r"\s+", " ", (h or "").strip()).lower()


def parse_csv_bytes(data: bytes) -> ParsedCSV:
    text = decode_csv_bytes(data)
    digest = file_sha256(data)
    # csv module
    try:
        reader = csv.reader(io.StringIO(text))
        all_rows = list(reader)
    except csv.Error as e:
        raise ImportParseError("malformed", "Malformed CSV") from e

    if not all_rows:
        raise ImportParseError("empty", "No rows in CSV")

    raw_headers = all_rows[0]
    if len(raw_headers) > MAX_COLUMNS:
        raise ImportParseError("too_many_columns", f"More than {MAX_COLUMNS} columns")

    headers = [normalize_header(h) for h in raw_headers]
    if any(not h for h in headers):
        raise ImportParseError("blank_header", "Blank header not allowed")
    if len(headers) != len(set(headers)):
        raise ImportParseError("dup_header", "Duplicate headers not allowed")

    body = all_rows[1:]
    if len(body) > MAX_ROWS:
        raise ImportParseError("too_many_rows", f"More than {MAX_ROWS} data rows")

    rows: List[Dict[str, str]] = []
    for i, cells in enumerate(body, start=2):
        # skip fully empty lines
        if not any((c or "").strip() for c in cells):
            continue
        # pad/truncate to headers
        padded = list(cells) + [""] * max(0, len(headers) - len(cells))
        padded = padded[: len(headers)]
        row: Dict[str, str] = {}
        for h, v in zip(headers, padded):
            val = (v or "").strip()
            if len(val) > MAX_FIELD_LEN:
                raise ImportParseError(
                    "field_too_long",
                    f"Row {i} field exceeds {MAX_FIELD_LEN} characters",
                )
            row[h] = val
        rows.append(row)

    return ParsedCSV(
        headers=headers,
        rows=rows,
        file_hash=digest,
        raw_row_count=len(rows),
    )


def neutralize_formula_cell(value: str) -> str:
    """Prevent CSV formula injection in exported reports."""
    if value is None:
        return ""
    s = str(value)
    if s[:1] in ("=", "+", "-", "@"):
        return "'" + s
    return s


def write_safe_csv(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([neutralize_formula_cell(h) for h in headers])
    for row in rows:
        w.writerow([neutralize_formula_cell("" if c is None else c) for c in row])
    return buf.getvalue()
