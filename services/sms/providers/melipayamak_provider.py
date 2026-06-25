import logging
import os
from typing import Any, Dict

from services.sms.providers.base import (
    SMSProvider,
    SMSProviderConfigurationError,
    SMSProviderPermanentError,
    SMSProviderTemporaryError,
)


class MelipayamakProvider(SMSProvider):
    """
    Melipayamak provider adapter.
    Uses official client flow:
      api = Api(username, password)
      sms = api.sms("rest"|"soap")
      sms.send(to, _from, text, ...)
    """

    def __init__(
        self,
        username: str,
        password: str,
        line_number: str,
        use_soap: bool = False,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.username = username
        self.password = password
        self.line_number = line_number
        self.use_soap = use_soap

    @classmethod
    def from_env(cls) -> "MelipayamakProvider":
        username = (os.environ.get("MELIPAYAMAK_USERNAME") or "").strip()
        password = (os.environ.get("MELIPAYAMAK_PASSWORD") or "").strip()
        line_number = (os.environ.get("MELIPAYAMAK_LINE_NUMBER") or "").strip()
        use_soap = (os.environ.get("MELIPAYAMAK_USE_SOAP", "0") or "0").strip() == "1"

        missing = []
        if not username:
            missing.append("MELIPAYAMAK_USERNAME")
        if not password:
            missing.append("MELIPAYAMAK_PASSWORD")
        if not line_number:
            missing.append("MELIPAYAMAK_LINE_NUMBER")

        if missing:
            raise SMSProviderConfigurationError(
                "Missing SMS config: " + ", ".join(missing)
            )

        return cls(
            username=username,
            password=password,
            line_number=line_number,
            use_soap=use_soap,
        )

    def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        if not recipient or not recipient.strip():
            raise SMSProviderPermanentError("Recipient phone is required")
        if not message or not message.strip():
            raise SMSProviderPermanentError("Message body is required")

        try:
            from melipayamak import Api
        except Exception as exc:
            raise SMSProviderConfigurationError(
                "melipayamak package is not installed. Install dependency 'melipayamak'."
            ) from exc

        try:
            api = Api(self.username, self.password)
            method = "soap" if self.use_soap else "rest"
            sms = api.sms(method)
            if self.use_soap:
                raw_response = sms.send(
                    to=recipient.strip(),
                    _from=self.line_number,
                    text=message.strip(),
                    isflash=False,
                )
            else:
                raw_response = sms.send(
                    to=recipient.strip(),
                    _from=self.line_number,
                    text=message.strip(),
                    isFlash=False,
                )

            provider_message_id = self._extract_message_id(raw_response)
            return {
                "provider_message_id": provider_message_id,
                "raw_response": raw_response,
            }
        except (SMSProviderConfigurationError, SMSProviderPermanentError):
            raise
        except Exception as exc:
            error_text = str(exc).lower()
            if any(
                word in error_text
                for word in ("timeout", "tempor", "connection", "network", "unreachable")
            ):
                raise SMSProviderTemporaryError(str(exc)) from exc
            raise SMSProviderPermanentError(str(exc)) from exc

    @staticmethod
    def _extract_message_id(raw_response: Any) -> str | None:
        if raw_response is None:
            return None

        # REST responses may be dict/list/string depending on client behavior.
        if isinstance(raw_response, dict):
            for key in ("Value", "value", "message_id", "messageId", "id"):
                if key in raw_response and raw_response[key] is not None:
                    return str(raw_response[key])
            return str(raw_response)[:100]

        if isinstance(raw_response, (list, tuple)):
            if not raw_response:
                return None
            return str(raw_response[0])[:100]

        return str(raw_response)[:100]
