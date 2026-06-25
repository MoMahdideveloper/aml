from services.llm.providers.gemini_provider import GeminiProvider


def test_analyze_multimodal_context_returns_deterministic_fallback_without_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    provider = GeminiProvider()
    provider.client = None

    result = provider.analyze_multimodal_context({"property_id": "prop-1", "title": "Demo"})
    assert result["property_id"] == "prop-1"
    assert result["smart_benefits"] == [{"benefit": "Great potential."}]
    assert result["trending_badges"] == []
