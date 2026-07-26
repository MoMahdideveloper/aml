"""Tests for GeminiEmbeddingProvider vector hygiene.

Covers two failure modes that are invisible from the outside:
  * resized vectors losing unit length, which silently distorts every cosine
    score compared against the matcher threshold
  * the non-semantic hash fallback being returned without any warning, making a
    degraded provider look identical to healthy semantic search
"""

import logging
import math

import pytest

from services.embeddings.providers.gemini_embedding_provider import (
    GeminiEmbeddingProvider,
)

_CREDENTIAL_ENV_VARS = (
    "GEMINI_EMBED_API_KEYS",
    "GEMINI_EMBED_API_KEY",
    "GOOGLE_EMBED_API_KEY",
    "GOOGLE_API_KEYS",
)


def _magnitude(values):
    return math.sqrt(sum(component * component for component in values))


@pytest.fixture
def provider(monkeypatch):
    """Keyless provider with a small dimension.

    Clearing every credential variable keeps the constructor offline: no client
    is built, so no test here can make a network call or consume free-tier quota.
    """
    for name in _CREDENTIAL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EMBEDDING_DIM", "4")
    instance = GeminiEmbeddingProvider()
    assert instance.client is None, "provider must stay offline in unit tests"
    return instance


class TestVectorNormalization:
    """_truncate_or_pad must always hand back a unit-length vector."""

    def test_truncation_renormalizes(self, provider):
        # Unit-length across 6 dims; slicing to 4 drops magnitude below 1.
        source = [1 / math.sqrt(6)] * 6
        assert _magnitude(source) == pytest.approx(1.0)

        result = provider._truncate_or_pad(source)

        assert len(result) == 4
        assert _magnitude(result) == pytest.approx(1.0)

    def test_padding_renormalizes(self, provider):
        # Zero-padding grows the dimension without touching magnitude (5.0).
        result = provider._truncate_or_pad([3.0, 4.0])

        assert len(result) == 4
        assert _magnitude(result) == pytest.approx(1.0)
        assert result == pytest.approx([0.6, 0.8, 0.0, 0.0])

    def test_exact_dimension_still_normalizes(self, provider):
        result = provider._truncate_or_pad([2.0, 0.0, 0.0, 0.0])

        assert _magnitude(result) == pytest.approx(1.0)
        assert result == pytest.approx([1.0, 0.0, 0.0, 0.0])

    def test_direction_is_preserved(self, provider):
        """Normalizing may only scale the vector, never rotate it."""
        source = [1.0, 2.0, 3.0, 4.0]

        result = provider._truncate_or_pad(source)

        ratios = [out / src for out, src in zip(result, source)]
        assert ratios == pytest.approx([ratios[0]] * 4)

    def test_zero_vector_does_not_divide_by_zero(self, provider):
        result = provider._truncate_or_pad([0.0, 0.0, 0.0, 0.0])

        assert result == [0.0, 0.0, 0.0, 0.0]

    def test_already_unit_vector_is_unchanged(self, provider):
        source = [0.5, 0.5, 0.5, 0.5]
        assert _magnitude(source) == pytest.approx(1.0)

        assert provider._truncate_or_pad(source) == pytest.approx(source)


class TestFallbackVisibility:
    """The hash fallback carries no meaning, so it must never be silent."""

    def test_fallback_logs_a_warning(self, provider, caplog):
        with caplog.at_level(logging.WARNING):
            vector = provider._fallback_vector("a quiet studio near the park")

        assert len(vector) == 4
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "fallback embedding must warn"
        assert "fallback" in warnings[0].getMessage().lower()

    def test_fallback_warning_excludes_embedded_text(self, provider, caplog):
        """Embedded content includes customer PII; only the length may be logged."""
        secret = "Jane Doe jane.doe@example.com +1-555-0100"

        with caplog.at_level(logging.WARNING):
            provider._fallback_vector(secret)

        logged = " ".join(r.getMessage() for r in caplog.records)
        assert secret not in logged
        assert "jane.doe@example.com" not in logged
        assert str(len(secret)) in logged

    def test_fallback_reason_is_reported(self, provider, caplog):
        with caplog.at_level(logging.WARNING):
            provider._fallback_vector("text", reason="quota exhausted")

        logged = " ".join(r.getMessage() for r in caplog.records)
        assert "quota exhausted" in logged

    def test_fallback_is_deterministic(self, provider):
        assert provider._fallback_vector("same") == provider._fallback_vector("same")

    def test_embed_without_client_warns_for_every_text(self, provider, caplog):
        with caplog.at_level(logging.WARNING):
            vectors = provider.embed(["first listing", "second listing"])

        assert len(vectors) == 2
        assert all(len(vector) == 4 for vector in vectors)
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 2
        assert "not initialized" in warnings[0].getMessage()

    def test_embed_of_empty_list_is_quiet(self, provider, caplog):
        with caplog.at_level(logging.WARNING):
            assert provider.embed([]) == []

        assert not [r for r in caplog.records if r.levelno == logging.WARNING]
