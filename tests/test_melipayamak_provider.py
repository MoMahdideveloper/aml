import types

import pytest

from services.sms.providers.base import (
    SMSProviderConfigurationError,
    SMSProviderPermanentError,
    SMSProviderTemporaryError,
)
from services.sms.providers.melipayamak_provider import MelipayamakProvider


def test_melipayamak_provider_from_env_missing_values(monkeypatch):
    monkeypatch.delenv("MELIPAYAMAK_USERNAME", raising=False)
    monkeypatch.delenv("MELIPAYAMAK_PASSWORD", raising=False)
    monkeypatch.delenv("MELIPAYAMAK_LINE_NUMBER", raising=False)

    with pytest.raises(SMSProviderConfigurationError) as exc:
        MelipayamakProvider.from_env()

    assert "MELIPAYAMAK_USERNAME" in str(exc.value)
    assert "MELIPAYAMAK_PASSWORD" in str(exc.value)
    assert "MELIPAYAMAK_LINE_NUMBER" in str(exc.value)


def test_melipayamak_provider_send_message_success(monkeypatch):
    class _SmsClient:
        def send(self, to, _from, text, isFlash=False):
            assert to == "09121234567"
            assert _from == "1000"
            assert text == "hello"
            assert isFlash is False
            return {"Value": "msg-999"}

    class _Api:
        def __init__(self, username, password):
            assert username == "user"
            assert password == "pass"

        def sms(self, method):
            assert method == "rest"
            return _SmsClient()

    fake_module = types.SimpleNamespace(Api=_Api)
    monkeypatch.setitem(__import__("sys").modules, "melipayamak", fake_module)

    provider = MelipayamakProvider(
        username="user",
        password="pass",
        line_number="1000",
        use_soap=False,
    )
    result = provider.send_message("09121234567", "hello")

    assert result["provider_message_id"] == "msg-999"


def test_melipayamak_provider_send_message_temporary_error(monkeypatch):
    class _SmsClient:
        def send(self, to, _from, text, isFlash=False):
            raise RuntimeError("timeout while connecting")

    class _Api:
        def __init__(self, username, password):
            pass

        def sms(self, method):
            return _SmsClient()

    fake_module = types.SimpleNamespace(Api=_Api)
    monkeypatch.setitem(__import__("sys").modules, "melipayamak", fake_module)

    provider = MelipayamakProvider("u", "p", "1000")
    with pytest.raises(SMSProviderTemporaryError):
        provider.send_message("09121234567", "hello")


def test_melipayamak_provider_send_message_permanent_error(monkeypatch):
    class _SmsClient:
        def send(self, to, _from, text, isFlash=False):
            raise RuntimeError("invalid sender")

    class _Api:
        def __init__(self, username, password):
            pass

        def sms(self, method):
            return _SmsClient()

    fake_module = types.SimpleNamespace(Api=_Api)
    monkeypatch.setitem(__import__("sys").modules, "melipayamak", fake_module)

    provider = MelipayamakProvider("u", "p", "1000")
    with pytest.raises(SMSProviderPermanentError):
        provider.send_message("09121234567", "hello")
