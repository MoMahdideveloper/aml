"""Mock extractor for zero-cost browser/staging smoke."""

import os

from services.ai_form_assist.gemini_extractor import GeminiFormExtractor
from services.ai_form_assist.mock_extractor import mock_extract


def test_mock_property_from_text():
    r = mock_extract(
        form="property",
        text="Modern Villa\n3 bed 2 bath 120 sqm price 2500000 for sale\naddress: 12 Oak St",
    )
    fields = {s.field: s.value for s in r.suggestions}
    assert r.model_id == "mock-extractor"
    assert "title" in fields
    assert fields.get("bedrooms") == 3
    assert fields.get("bathrooms") == 2
    assert fields.get("sale_price") == 2500000
    assert fields.get("listing_type") == "sale"


def test_mock_customer_budget():
    r = mock_extract(
        form="customer",
        text="name: Sara Buyer\nbudget 800000 2 bedroom apartment location: Downtown",
    )
    fields = {s.field: s.value for s in r.suggestions}
    assert fields.get("name") == "Sara Buyer"
    assert fields.get("budget_max") == 800000
    assert fields.get("preferred_bedrooms") == 2


def test_gemini_extractor_respects_mock_env(monkeypatch):
    monkeypatch.setenv("AI_FORM_ASSIST_MOCK", "1")
    ex = GeminiFormExtractor(client=None)
    r = ex.extract(form="task", text="Call client urgent due 2026-08-01")
    assert r.model_id == "mock-extractor"
    fields = {s.field: s.value for s in r.suggestions}
    assert "title" in fields
    assert fields.get("priority") == "urgent"


def test_mock_off_without_client_degrades(monkeypatch):
    monkeypatch.setenv("AI_FORM_ASSIST_MOCK", "0")
    ex = GeminiFormExtractor(client=None)
    r = ex.extract(form="property", text="x")
    assert r.degraded is True or r.suggestions == []
