"""Unit tests for Google Gemini key/model rotation and A6API separation."""

from types import SimpleNamespace


def test_chat_google_key_rotates_on_rate_limit(monkeypatch):
    from services.llm.providers import gemini_provider as module

    monkeypatch.setenv("GOOGLE_API_KEYS", "google-key-1,google-key-2")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    clients = []

    def fake_client(**kwargs):
        key = kwargs["api_key"]
        clients.append(kwargs)

        class Models:
            def generate_content(self, **request):
                if key == "google-key-1":
                    raise RuntimeError("429 RESOURCE_EXHAUSTED")
                return SimpleNamespace(text="ok")

        return SimpleNamespace(models=Models())

    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=fake_client))

    provider = module.GeminiProvider()

    assert provider._generate_text("hello") == "ok"
    assert [call["api_key"] for call in clients] == ["google-key-1", "google-key-2"]


def test_chat_quota_error_skips_remaining_models_on_exhausted_key(monkeypatch):
    from services.llm.providers import gemini_provider as module

    monkeypatch.setenv("GOOGLE_API_KEYS", "google-key-1,google-key-2")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "model-1")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACKS", "model-1,model-2,model-3")
    calls = []

    def fake_client(**kwargs):
        key = kwargs["api_key"]

        class Models:
            def generate_content(self, **request):
                calls.append((key, request["model"]))
                if key == "google-key-1":
                    raise RuntimeError("429 RESOURCE_EXHAUSTED")
                return SimpleNamespace(text="ok")

        return SimpleNamespace(models=Models())

    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=fake_client))
    provider = module.GeminiProvider()

    assert provider._generate_text("hello") == "ok"
    assert calls == [("google-key-1", "model-1"), ("google-key-2", "model-1")]


def test_chat_a6api_key_stays_separate(monkeypatch):
    from services.llm.providers import gemini_provider as module

    monkeypatch.setenv("GOOGLE_API_KEYS", "google-key")
    monkeypatch.setenv("GEMINI_API_KEY", "google-legacy-key")
    monkeypatch.setenv("GEMINI_A6API_API_KEY", "a6-key")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://a6.a6api.com")
    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=lambda **kwargs: kwargs))

    provider = module.GeminiProvider()

    assert provider.credential_provider == "google"
    assert provider.api_keys == ["google-key"]
    assert provider.base_url == ""
    assert provider.a6api_api_key == "a6-key"


def test_embeddings_rotate_keys_and_models(monkeypatch):
    from services.embeddings.providers import gemini_embedding_provider as module

    monkeypatch.setenv("GEMINI_EMBED_API_KEYS", "embed-key-1,embed-key-2")
    monkeypatch.delenv("GEMINI_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_EMBED_MODELS", "gemini-embedding-1,gemini-embedding-2")
    clients = []

    def fake_client(**kwargs):
        key = kwargs["api_key"]
        clients.append(kwargs)

        class Models:
            def embed_content(self, **request):
                if key == "embed-key-1":
                    raise RuntimeError("429 quota exceeded")
                if request["model"] == "gemini-embedding-1":
                    raise RuntimeError("404 NOT_FOUND")
                # Batched: return one embedding per input text
                texts = request["contents"]
                return SimpleNamespace(
                    embeddings=[SimpleNamespace(values=[0.25, 0.5]) for _ in texts]
                )

        return SimpleNamespace(models=Models())

    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=fake_client))

    provider = module.GeminiEmbeddingProvider()
    vectors = provider.embed(["hello"])

    assert len(vectors) == 1
    assert len(vectors[0]) == provider.dimension
    # The provider should have tried key-1 (all models failed), then key-2 (model-1
    # failed, model-2 succeeded). The mock records every _client_for call, which may
    # include retries, so just verify both keys were attempted.
    keys_tried = [call["api_key"] for call in clients]
    assert "embed-key-1" in keys_tried
    assert "embed-key-2" in keys_tried


def test_a6api_fallback_uses_only_a6_key_and_endpoint(monkeypatch):
    from services.llm.providers import gemini_provider as module

    monkeypatch.setenv("GOOGLE_API_KEYS", "google-key")
    monkeypatch.setenv("GEMINI_A6API_API_KEY", "a6-key")
    monkeypatch.setenv("GEMINI_A6API_BASE_URL", "https://a6.a6api.com")
    clients = []

    def fake_client(**kwargs):
        clients.append(kwargs)

        class Models:
            def generate_content(self, **request):
                if kwargs["api_key"] == "google-key":
                    raise RuntimeError("429 RESOURCE_EXHAUSTED")
                return SimpleNamespace(text="a6-ok")

        return SimpleNamespace(models=Models())

    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=fake_client))
    provider = module.GeminiProvider()

    assert provider._generate_text("hello") == "a6-ok"
    assert clients[0]["api_key"] == "google-key"
    assert clients[-1]["api_key"] == "a6-key"
    assert clients[-1]["http_options"].base_url == "https://a6.a6api.com"


def test_request_timeout_uses_supported_kwarg(monkeypatch):
    """The timeout must reach the SDK without raising TypeError.

    google-genai has no ``request_options`` parameter. Passing one made every
    first attempt raise TypeError, so the configured timeout never applied and
    each call silently retried with no timeout at all. Pin the supported shape:
    ``config.http_options.timeout``, in milliseconds.
    """
    from services.llm.providers import gemini_provider as module

    monkeypatch.setenv("GOOGLE_API_KEYS", "google-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "45")
    requests = []

    def fake_client(**kwargs):
        class Models:
            def generate_content(self, **request):
                # Mirror the real SDK: unknown kwargs are a hard TypeError.
                allowed = {"model", "contents", "config"}
                unexpected = set(request) - allowed
                if unexpected:
                    raise TypeError(
                        f"unexpected keyword argument {sorted(unexpected)[0]!r}"
                    )
                requests.append(request)
                return SimpleNamespace(text="ok")

        return SimpleNamespace(models=Models())

    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=fake_client))
    provider = module.GeminiProvider()

    assert provider._generate_text("hello") == "ok"
    # Exactly one call: no TypeError-triggered retry.
    assert len(requests) == 1
    assert "request_options" not in requests[0]
    assert requests[0]["config"].http_options.timeout == 45000


def test_request_timeout_omitted_when_disabled(monkeypatch):
    """A non-positive timeout sends no http_options at all."""
    from services.llm.providers import gemini_provider as module

    monkeypatch.setenv("GOOGLE_API_KEYS", "google-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "0")
    requests = []

    def fake_client(**kwargs):
        class Models:
            def generate_content(self, **request):
                requests.append(request)
                return SimpleNamespace(text="ok")

        return SimpleNamespace(models=Models())

    monkeypatch.setattr(module, "genai", SimpleNamespace(Client=fake_client))
    provider = module.GeminiProvider()

    assert provider._generate_text("hello") == "ok"
    assert "config" not in requests[0]
