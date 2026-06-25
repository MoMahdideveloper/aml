from typing import Any, Dict
import logging

from .base import SMSProvider

logger = logging.getLogger(__name__)

class LogProvider(SMSProvider):
    def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        """
        Log the message content instead of sending it.
        """
        logger.info(f"SMS TO {recipient}: {message}")
        return {
            "provider_message_id": "log-only-id",
            "status": "logged"
        }
