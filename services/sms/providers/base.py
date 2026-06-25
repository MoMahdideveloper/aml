from abc import ABC, abstractmethod
from typing import Any, Dict


class SMSProviderError(Exception):
    """Base provider error."""


class SMSProviderConfigurationError(SMSProviderError):
    """Configuration error that should fail immediately."""


class SMSProviderTemporaryError(SMSProviderError):
    """Transient provider error that can be retried."""


class SMSProviderPermanentError(SMSProviderError):
    """Permanent provider error that should not be retried."""


class SMSProvider(ABC):
    @abstractmethod
    def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        """
        Send a single message.
        Returns a dict with at least:
        - provider_message_id (optional)
        - raw_response (optional)
        """
        raise NotImplementedError
