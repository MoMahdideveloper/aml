"""Optional NL LLM parse is fail-open and soft-only."""

from services.nl_query_parse import try_llm_fill_soft_constraints
from services.query_constraints import QueryConstraints, extract_constraints


def test_disabled_returns_base(monkeypatch):
    monkeypatch.setenv("ENABLE_NL_QUERY_PARSE", "0")
    base = extract_constraints("something vague about homes")
    out = try_llm_fill_soft_constraints("something vague about homes", base)
    assert out is base or out.hard_filters() == base.hard_filters()


def test_provider_down_fail_open(monkeypatch):
    monkeypatch.setenv("ENABLE_NL_QUERY_PARSE", "1")
    import services.nl_query_parse as mod

    monkeypatch.setattr(mod, "feature_enabled", lambda: True)

    class _Down:
        is_available = False

    # Patch llm import inside try
    import services.llm as llm_mod

    monkeypatch.setattr(llm_mod, "llm_provider", _Down(), raising=False)
    base = QueryConstraints()
    out = try_llm_fill_soft_constraints("nice place with parking", base)
    assert out.hard_filters() == {}


def test_does_not_override_hard_rule_fields(monkeypatch):
    monkeypatch.setenv("ENABLE_NL_QUERY_PARSE", "1")
    import services.nl_query_parse as mod

    monkeypatch.setattr(mod, "feature_enabled", lambda: True)

    class _FakeLLM:
        is_available = True

        def generate_market_analysis(self, prompt):
            return '{"bedrooms_min": 9, "property_type": "castle"}'

    import services.llm as llm_mod

    monkeypatch.setattr(llm_mod, "llm_provider", _FakeLLM(), raising=False)
    base = extract_constraints("3 bedroom apartment")
    assert base.bedrooms_min == 3
    out = try_llm_fill_soft_constraints("3 bedroom apartment", base)
    # rule high confidence remains hard; LLM must not replace bedrooms_min
    assert out.bedrooms_min == 3
    assert out.confidences.get("bedrooms_min", 0) >= 0.8
