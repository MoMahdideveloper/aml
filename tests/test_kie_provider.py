import importlib

from services.llm.providers.kie_provider import KieProvider


class _FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_llm_provider_selects_kie(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "kie")
    monkeypatch.setenv("KIE_API_KEY", "test-key")

    module = importlib.import_module("services.llm")
    module = importlib.reload(module)

    assert isinstance(module.llm_provider, KieProvider)
    assert module.llm_provider.is_available is True


def test_kie_provider_market_analysis_text(monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-key")
    provider = KieProvider()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": "Overview: Stable demand.\n- Inventory tightening\n- Price growth moderating"
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("services.llm.providers.kie_provider.requests.post", _fake_post)
    result = provider.generate_market_analysis("prompt")
    assert "Stable demand" in result


def test_kie_provider_extract_property_json_code_fence(monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-key")
    provider = KieProvider()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": "```json\n{\"title\":\"Demo\",\"bedrooms\":2,\"bathrooms\":1}\n```"
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("services.llm.providers.kie_provider.requests.post", _fake_post)
    parsed = provider.extract_property("sample")
    assert parsed.get("title") == "Demo"
    assert parsed.get("bedrooms") == 2


def test_kie_provider_handles_http_error(monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-key")
    provider = KieProvider()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(401, {"error": "unauthorized"}, "unauthorized")

    monkeypatch.setattr("services.llm.providers.kie_provider.requests.post", _fake_post)
    parsed = provider.extract_customer("sample")
    assert parsed == {}
