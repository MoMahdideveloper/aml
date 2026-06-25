import logging
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from database import db
from sqlalchemy_models import SmsOutboundMessage
from services.sms.providers import (
    MelipayamakProvider,
    LogProvider,
    SMSProviderConfigurationError,
    SMSProviderPermanentError,
    SMSProviderTemporaryError,
)
from utils.execution_tracer import log_execution


class SMSService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    @log_execution
    def queue_messages(
        self,
        recipients: Iterable[str],
        message: str,
        created_by_user_id: Optional[int] = None,
        provider: Optional[str] = None,
        max_attempts: int = 3,
    ) -> List[SmsOutboundMessage]:
        provider_name = (provider or os.environ.get("SMS_PROVIDER", "melipayamak")).strip().lower()
        clean_message = (message or "").strip()
        if not clean_message:
            raise ValueError("Message body is required")

        if isinstance(recipients, str):
            candidates: Iterable[str] = [recipients]
        else:
            candidates = recipients

        recipient_list: List[str] = []
        for raw in candidates:
            phone = self._normalize_phone(raw)
            if phone:
                recipient_list.append(phone)

        if not recipient_list:
            raise ValueError("At least one valid recipient is required")

        # Keep order while deduplicating.
        unique_recipients = list(dict.fromkeys(recipient_list))
        queued: List[SmsOutboundMessage] = []
        for recipient in unique_recipients:
            msg = SmsOutboundMessage(
                recipient=recipient,
                message=clean_message,
                provider=provider_name,
                status="pending",
                attempts=0,
                max_attempts=max(1, int(max_attempts or 3)),
                created_by_user_id=created_by_user_id,
            )
            db.session.add(msg)
            queued.append(msg)

        db.session.commit()
        return queued

    @log_execution
    def get_history(self, limit: int = 50, status: Optional[str] = None) -> List[SmsOutboundMessage]:
        query = SmsOutboundMessage.query.order_by(SmsOutboundMessage.created_at.desc())
        if status:
            query = query.filter(SmsOutboundMessage.status == status)
        return query.limit(max(1, min(int(limit or 50), 500))).all()

    @log_execution
    def process_queue(self, batch_size: int = 20) -> Dict[str, int]:
        provider_cache: Dict[str, Any] = {}
        processed = 0
        sent = 0
        failed = 0
        retried = 0

        pending_messages = (
            SmsOutboundMessage.query.filter(SmsOutboundMessage.status == "pending")
            .order_by(SmsOutboundMessage.created_at.asc())
            .limit(max(1, int(batch_size or 20)))
            .all()
        )

        for msg in pending_messages:
            processed += 1
            provider_name = (msg.provider or "melipayamak").strip().lower()

            if msg.attempts >= msg.max_attempts:
                msg.status = "failed"
                msg.error_message = "Maximum retry attempts reached"
                failed += 1
                continue

            try:
                provider = provider_cache.get(provider_name)
                if provider is None:
                    provider = self._get_provider(provider_name)
                    provider_cache[provider_name] = provider

                result = provider.send_message(msg.recipient, msg.message)
                msg.status = "sent"
                msg.sent_at = datetime.utcnow()
                msg.error_message = None
                msg.provider_message_id = (
                    str(result.get("provider_message_id"))[:100]
                    if isinstance(result, dict) and result.get("provider_message_id") is not None
                    else None
                )
                sent += 1
            except SMSProviderConfigurationError as exc:
                # Config errors should fail messages immediately.
                msg.attempts += 1
                msg.status = "failed"
                msg.error_message = str(exc)
                failed += 1
                # Prevent rebuilding provider repeatedly in same cycle.
                provider_cache[provider_name] = _BrokenProvider(str(exc))
            except SMSProviderTemporaryError as exc:
                msg.attempts += 1
                msg.error_message = str(exc)
                if msg.attempts >= msg.max_attempts:
                    msg.status = "failed"
                    failed += 1
                else:
                    msg.status = "pending"
                    retried += 1
            except SMSProviderPermanentError as exc:
                msg.attempts += 1
                msg.status = "failed"
                msg.error_message = str(exc)
                failed += 1
            except Exception as exc:
                # Unknown failure path: retry until max_attempts.
                msg.attempts += 1
                msg.error_message = str(exc)
                if msg.attempts >= msg.max_attempts:
                    msg.status = "failed"
                    failed += 1
                else:
                    msg.status = "pending"
                    retried += 1

        db.session.commit()
        return {
            "processed": processed,
            "sent": sent,
            "failed": failed,
            "retried": retried,
        }

    @staticmethod
    @log_execution
    def _normalize_phone(raw: Any) -> Optional[str]:
        if raw is None:
            return None
        value = str(raw).strip()
        if not value:
            return None

        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            return None

        # Normalize common Iranian formats.
        if digits.startswith("98") and len(digits) >= 12:
            digits = "0" + digits[2:]
        if digits.startswith("0098") and len(digits) >= 14:
            digits = "0" + digits[4:]
        return digits

    @staticmethod
    @log_execution
    def _get_provider(provider_name: str):
        name = (provider_name or "melipayamak").strip().lower()

        if name == "log":
            return LogProvider()

        if name == "melipayamak":
            return MelipayamakProvider.from_env()

        raise SMSProviderConfigurationError(f"Unsupported SMS provider: {name}")


class _BrokenProvider:
    """Sentinel provider used to short-circuit repeated config failures in a batch."""

    def __init__(self, error_message: str) -> None:
        self.error_message = error_message

    @log_execution
    def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        raise SMSProviderConfigurationError(self.error_message)


sms_service = SMSService()
