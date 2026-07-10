"""Secure CSV parser tests."""

import pytest
from services.import_parser import (
    ImportParseError,
    neutralize_formula_cell,
    parse_csv_bytes,
    write_safe_csv,
)


def test_parse_valid_customer_csv():
    data = b"name,email,phone\nAda,ada@example.com,5551234567\n"
    parsed = parse_csv_bytes(data)
    assert parsed.headers == ["name", "email", "phone"]
    assert len(parsed.rows) == 1
    assert parsed.rows[0]["email"] == "ada@example.com"
    assert len(parsed.file_hash) == 64


def test_reject_binary_and_oversized():
    with pytest.raises(ImportParseError) as e:
        parse_csv_bytes(b"%PDF-1.4 fake")
    assert e.value.code == "not_csv"
    with pytest.raises(ImportParseError) as e2:
        parse_csv_bytes(b"a,b\n" + b"x" * (3 * 1024 * 1024))
    assert e2.value.code == "too_large"


def test_reject_duplicate_headers():
    with pytest.raises(ImportParseError) as e:
        parse_csv_bytes(b"name,name\nA,B\n")
    assert e.value.code == "dup_header"


def test_bom_and_quoted_fields():
    data = b"\xef\xbb\xbfname,email,phone\n\"Ann, A\",ann@ex.com,55599998888\n"
    parsed = parse_csv_bytes(data)
    assert parsed.rows[0]["name"] == "Ann, A"


def test_formula_neutralize_export():
    assert neutralize_formula_cell("=cmd|'/c calc'!A0").startswith("'")
    csv_out = write_safe_csv(["a"], [["=1+1"], ["ok"]])
    assert "'=1+1" in csv_out
