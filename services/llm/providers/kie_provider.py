import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

from sqlalchemy_models import Customer, Property
from services.llm.providers.base import LLMProvider


class KieProvider(LLMProvider):
    """KIE-hosted chat-completions provider compatible with the existing LLM interface."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.llm.providers.kie")
        self.api_key = os.environ.get("KIE_API_KEY")
        self.model = os.environ.get("KIE_MODEL", "gemini-2.5-flash").strip()
        self.base_url = os.environ.get("KIE_BASE_URL", "https://api.kie.ai").rstrip("/")
        self.timeout_seconds = float(os.environ.get("KIE_TIMEOUT_SECONDS", "45"))
        self.include_thoughts = os.environ.get("KIE_INCLUDE_THOUGHTS", "0") == "1"

        explicit_url = os.environ.get("KIE_CHAT_COMPLETIONS_URL")
        self.chat_url = (
            explicit_url.strip()
            if explicit_url
            else f"{self.base_url}/{self.model}/v1/chat/completions"
        )

        if not self.api_key:
            self.logger.warning("No KIE_API_KEY set; Kie provider disabled")

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _content_text(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if not isinstance(content, list):
            return ""

        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif item.get("type") == "text" and isinstance(item.get("value"), str):
                    parts.append(item["value"])
        return "\n".join(p.strip() for p in parts if p).strip()

    def _extract_text_from_response(self, payload: Dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""

        first = choices[0] or {}
        if not isinstance(first, dict):
            return ""

        message = first.get("message")
        if isinstance(message, dict):
            text = self._content_text(message.get("content"))
            if text:
                return text

        return self._content_text(first.get("content"))

    def _chat_completion(self, prompt: str) -> str:
        if not self.api_key:
            return ""

        request_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            "stream": False,
            "include_thoughts": self.include_thoughts,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.chat_url,
                headers=headers,
                json=request_payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            self.logger.warning("KIE request failed: %s", exc)
            return ""

        if response.status_code >= 400:
            snippet = response.text[:300]
            self.logger.warning(
                "KIE request returned status %s: %s",
                response.status_code,
                snippet,
            )
            return ""

        try:
            body = response.json()
        except Exception as exc:
            self.logger.warning("KIE response JSON parse failed: %s", exc)
            return ""

        if not isinstance(body, dict):
            return ""
        return self._extract_text_from_response(body)

    def _chat_completion_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a chat-completions request with OpenAI-compatible tool definitions.

        Returns the full parsed response dict so callers can inspect
        ``choices[0].message.tool_calls`` for function-calling results.
        Returns ``{}`` on any failure.
        """
        if not self.api_key:
            return {}

        request_payload: Dict[str, Any] = {
            "messages": messages,
            "stream": False,
            "include_thoughts": self.include_thoughts,
        }
        if tools:
            request_payload["tools"] = tools
            request_payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.chat_url,
                headers=headers,
                json=request_payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            self.logger.warning("KIE tools request failed: %s", exc)
            return {}

        if response.status_code >= 400:
            snippet = response.text[:300]
            self.logger.warning(
                "KIE tools request returned status %s: %s",
                response.status_code,
                snippet,
            )
            return {}

        try:
            body = response.json()
        except Exception as exc:
            self.logger.warning("KIE tools response JSON parse failed: %s", exc)
            return {}

        return body if isinstance(body, dict) else {}

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        if not text:
            return {}

        code_fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if code_fence:
            candidate = code_fence.group(1)
            try:
                parsed = json.loads(candidate)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}

        try:
            parsed = json.loads(match.group())
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def generate_recommendation_reasoning(
        self,
        customer: Customer,
        property_obj: Property,
        reasons: List[str],
        score: float,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        fallback = {
            "explanation": f"This property has a match score of {score:.1f}/100 based on your preferences.",
            "pros": reasons,
            "cons": [],
        }
        if not self.is_available:
            return fallback

        # Build conversation history text if provided
        history_text = ""
        if conversation_history:
            history_parts = []
            for turn in conversation_history[-5:]:  # Last 5 turns for context
                role = turn.get("role", "unknown")
                parts = turn.get("parts", [])
                text_parts = []
                for part in parts:
                    if isinstance(part, dict):
                        txt = str(part.get("text") or "").strip()
                        if txt:
                            text_parts.append(txt)
                    elif isinstance(part, str):
                        txt = str(part or "").strip()
                        if txt:
                            text_parts.append(txt)
                if text_parts:
                    history_parts.append(f"{role}: {' '.join(text_parts)}")
            if history_parts:
                history_text = "\nRecent conversation:\n" + "\n".join(history_parts) + "\n"

        prompt = (
            "As a real estate expert, return ONLY JSON with keys explanation, pros, cons. "
            f"Customer wants type={customer.preferred_type}, location={customer.location_preference}, "
            f"beds={customer.preferred_bedrooms}, baths={customer.preferred_bathrooms}, "
            f"budget={customer.budget_min}-{customer.budget_max}. "
            f"Property={property_obj.address}, type={property_obj.property_type}, neighborhood={property_obj.neighborhood}, "
            f"price={property_obj.price}, beds={property_obj.bedrooms}, baths={property_obj.bathrooms}. "
            f"Reasons={reasons}. Score={score:.1f}."
            f"{history_text}"
        )
        text = self._chat_completion(prompt)
        parsed = self._extract_json(text)
        if not parsed:
            return fallback

        return {
            "explanation": str(parsed.get("explanation", fallback["explanation"])),
            "pros": list(parsed.get("pros", reasons))[:5],
            "cons": list(parsed.get("cons", []))[:5],
        }

    def extract_property(self, blob: str) -> Dict[str, Any]:
        if not self.is_available:
            return {}
        prompt = (
            "Extract property fields into strict JSON. "
            "Keys: title,address,price,property_type,bedrooms,bathrooms,square_feet,description,status,"
            "year_built,parking_spaces,floors,units,property_condition,property_features,neighborhood,"
            "property_category,listing_type,rahn,ejare. Use null when unknown.\n"
            f"TEXT:\n{blob}"
        )
        return self._extract_json(self._chat_completion(prompt))

    def extract_customer(self, blob: str) -> Dict[str, Any]:
        if not self.is_available:
            return {}
        prompt = (
            "Extract customer fields into strict JSON. "
            "Keys: name,email,phone,preferences,budget_min,budget_max,desired_neighborhoods,"
            "desired_property_type,bedrooms_min,bathrooms_min. Use null when unknown.\n"
            f"TEXT:\n{blob}"
        )
        return self._extract_json(self._chat_completion(prompt))

    def generate_market_analysis(self, prompt: str) -> str:
        return self._chat_completion(prompt).strip()
