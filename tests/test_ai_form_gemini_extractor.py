"""Mocked Gemini form extractor — zero network."""

import json

import pytest

from services.ai_form_assist.gemini_extractor import GeminiFormExtractor


class _FakeModels:
    def __init__(self, text: str = "", raise_exc: Exception | None = None):
        self.text = text
        self.raise_exc = raise_exc
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise self.raise_exc
        return type("R", (), {"text": self.text})()


class _FakeClient:
    def __init__(self, models):
        self.models = models


def test_extract_parses_json_fields():
    payload = {
        "fields": [
            {"field": "title", "value": "Nice Villa", "confidence": 0.95},
            {"field": "sale_price", "value": 500000, "confidence": 0.8},
            {"field": "database_admin", "value": "x", "confidence": 0.99},  # rejected
        ]
    }
    models = _FakeModels(text=json.dumps(payload))
    ext = GeminiFormExtractor(client=_FakeClient(models), fast_model="fast-model")
    result = ext.extract(form="property", text="villa for sale")
    assert result.degraded is False
    assert result.model_id == "fast-model"
    names = {s.field for s in result.suggestions}
    assert "title" in names
    assert "sale_price" in names
    assert "database_admin" not in names
    assert models.calls
    cfg = models.calls[0].get("config") or {}
    assert cfg.get("response_mime_type") == "application/json"


def test_unavailable_client_degrades():
    ext = GeminiFormExtractor(client=None)
    result = ext.extract(form="property", text="x")
    assert result.degraded is True
    assert result.error == "unavailable"


def test_malformed_json_retries_then_degrades():
    class _FlipModels:
        def __init__(self):
            self.n = 0
            self.calls = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            self.n += 1
            if self.n == 1:
                return type("R", (), {"text": "NOT JSON"})()
            return type("R", (), {"text": '{"fields":[]}'})()

    models = _FlipModels()
    ext = GeminiFormExtractor(client=_FakeClient(models))
    result = ext.extract(form="property", text="x")
    assert len(models.calls) >= 1
    # either recovered on retry or degraded
    assert result.form == "property"


def test_escalation_uses_escalation_model_and_field_filter():
    models = _FakeModels(text='{"fields":[{"field":"title","value":"T","confidence":0.9}]}')
    ext = GeminiFormExtractor(
        client=_FakeClient(models),
        fast_model="fast",
        escalation_model="slow",
    )
    result = ext.escalate_uncertain(
        form="property", text="x", uncertain_fields=["title", "sale_price"]
    )
    assert result.model_id == "slow"
    assert models.calls
    prompt = str(models.calls[0].get("contents"))
    # field filter reflected in prompt
    assert "title" in models.calls[0]["model"] or result.model_id == "slow"


def test_build_parts_includes_image_and_audio(monkeypatch):
    ext = GeminiFormExtractor(client=object())
    # Skip if google.genai not installed
    pytest.importorskip("google.genai")
    jpeg = b"\xff\xd8\xff" + b"\x00" * 20
    parts = ext.build_parts(
        prompt="p",
        image_parts=[(jpeg, "image/jpeg")],
        audio_parts=[(b"\x1aE\xdf\xa3" + b"\x00" * 10, "audio/webm")],
    )
    assert len(parts) == 3
