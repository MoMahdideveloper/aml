"""Persian-first value normalization."""

from datetime import date

import pytest

from services.ai_form_assist.normalization import (
    normalize_area,
    normalize_date,
    normalize_digits,
    normalize_enum,
    normalize_field_value,
    normalize_money,
    normalize_phone,
)


def test_persian_digits():
    assert normalize_digits("۱۲۳۴") == "1234"


def test_money_persian_million():
    assert normalize_money("۵ میلیون تومان") == 5_000_000.0


def test_money_k_suffix():
    assert normalize_money("500k") == 500_000.0


def test_area_meters():
    assert normalize_area("۱۲۰ متر مربع") == 120


def test_phone_iran_local():
    assert normalize_phone("09121234567") == "+989121234567"


def test_date_iso():
    assert normalize_date("2026-07-13") == "2026-07-13"


def test_relative_date_requires_reference():
    assert normalize_date("today") is None
    assert normalize_date("today", reference=date(2026, 7, 13)) == "2026-07-13"


def test_enum_listing_type():
    assert normalize_enum("اجاره", ["sale", "rental"]) == "rental"
    assert normalize_enum("sale", ["sale", "rental"]) == "sale"


def test_normalize_field_value_dispatch():
    assert normalize_field_value("number", "۲۰۰۰") == 2000.0
    assert normalize_field_value("integer", "۳") == 3
    assert normalize_field_value("string", "  hello  ") == "hello"
