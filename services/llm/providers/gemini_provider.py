import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

try:
    from google import genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None

from sqlalchemy_models import Customer, Property
from services.llm.providers.base import LLMProvider


# A6API-preferred Gemini models (OpenAI-compatible /v1 or native /v1beta).
# Override via GEMINI_MODEL / GEMINI_MODEL_FALLBACKS.
_DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
_DEFAULT_MODEL_FALLBACKS = (
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash",
)


def _split_keys(raw: str) -> List[str]:
    return [part.strip().strip('"').strip("'") for part in (raw or "").split(",") if part.strip()]


class GeminiProvider(LLMProvider):
    """Gemini-first provider using the newer google-genai SDK."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.llm.providers.gemini")
        self.model = (
            os.environ.get("GEMINI_MODEL", _DEFAULT_GEMINI_MODEL).strip()
            or _DEFAULT_GEMINI_MODEL
        )
        raw_fallbacks = os.environ.get("GEMINI_MODEL_FALLBACKS", "").strip()
        if raw_fallbacks:
            fallbacks = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]
        else:
            fallbacks = list(_DEFAULT_MODEL_FALLBACKS)
        # Primary first, then unique fallbacks (skip duplicates of primary).
        ordered: List[str] = [self.model]
        for m in fallbacks:
            if m not in ordered:
                ordered.append(m)
        self.models = ordered
        self.request_timeout_seconds = int(os.environ.get("GEMINI_REQUEST_TIMEOUT_SECONDS", "45"))
        self.max_retries = max(0, int(os.environ.get("GEMINI_REQUEST_RETRIES", "1")))
        # Keep Google AI Studio and A6API credentials completely separate.
        self.a6api_api_key = os.environ.get("GEMINI_A6API_API_KEY", "").strip().strip('"').strip("'")
        google_keys = _split_keys(os.environ.get("GOOGLE_API_KEYS", ""))
        if not google_keys:
            google_keys = _split_keys(os.environ.get("GOOGLE_API_KEY", ""))
        if not google_keys:
            # Legacy alias for Google-native credentials only; never an A6API key.
            google_keys = _split_keys(os.environ.get("GEMINI_API_KEY", ""))
        self.google_api_keys = google_keys
        self.credential_provider = "google" if google_keys else "a6api"
        self.api_keys = google_keys or ([self.a6api_api_key] if self.a6api_api_key else [])
        self.api_key = self.api_keys[0] if self.api_keys else ""
        self.base_url = "" if google_keys else (
            os.environ.get("GEMINI_A6API_BASE_URL")
            or os.environ.get("GEMINI_BASE_URL")
            or os.environ.get("GOOGLE_GENAI_BASE_URL")
            or os.environ.get("GOOGLE_API_BASE")
            or ""
        ).strip().rstrip("/")
        self.client = None

        if genai is None:
            self.logger.warning("google-genai SDK not available; Gemini provider disabled")
            return

        if not self.api_keys:
            self.logger.warning("No Gemini API key set; Gemini provider disabled")
            return

        try:
            self.client = self._client_for(self.api_keys[0])
        except Exception as exc:  # pragma: no cover
            self.logger.warning(f"Failed to initialize Gemini client: {exc}")
            self.client = None

    def _client_for(self, api_key: str, base_url: Optional[str] = None):
        """Build a client bound to one credential and its provider endpoint."""
        kwargs: Dict[str, Any] = {"api_key": api_key}
        endpoint = self.base_url if base_url is None else base_url
        if endpoint:
            from google.genai import types as genai_types

            kwargs["http_options"] = genai_types.HttpOptions(base_url=endpoint)
        return genai.Client(**kwargs)

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def _extract_json_object(self, text: str) -> Optional[str]:
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return fenced.group(1)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return None

    def _generate_text_once(
        self,
        prompt: str,
        *,
        model: str,
        include_timeout: bool,
    ) -> str:
        if not self.client:
            return ""
        kwargs: Dict[str, Any] = {"model": model, "contents": prompt}
        if include_timeout and self.request_timeout_seconds > 0:
            kwargs["request_options"] = {"timeout": self.request_timeout_seconds}
        response = self.client.models.generate_content(**kwargs)
        text = getattr(response, "text", None)
        return text.strip() if isinstance(text, str) else ""

    def _generate_text(self, prompt: str) -> str:
        if not self.client:
            return ""
        from utils.observability import timed_provider

        last_exc: Optional[Exception] = None
        with timed_provider("gemini", "generate") as _obs:
            google_keys = self.google_api_keys or self.api_keys
            for key_index, api_key in enumerate(google_keys):
                if key_index:
                    try:
                        self.client = self._client_for(api_key)
                    except Exception as exc:
                        last_exc = exc
                        continue
                key_quota_exhausted = False
                for model in self.models:
                    for attempt in range(1, self.max_retries + 2):
                        try:
                            text = self._generate_text_once(
                                prompt, model=model, include_timeout=True
                            )
                            if text:
                                return text
                        except TypeError:
                            try:
                                text = self._generate_text_once(
                                    prompt, model=model, include_timeout=False
                                )
                                if text:
                                    return text
                            except Exception as exc:
                                last_exc = exc
                        except Exception as exc:
                            last_exc = exc
                            msg = str(exc)
                            if "404" in msg or "NOT_FOUND" in msg or "no longer available" in msg:
                                break
                            if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                                key_quota_exhausted = True
                                break
                            self.logger.warning(
                                "Gemini text generation failed model=%s attempt=%s: %s",
                                model,
                                attempt,
                                type(exc).__name__,
                            )
                    if key_quota_exhausted:
                        break
            # A6API is a separate provider fallback, with its own credential
            # and endpoint. Never send an A6API key to Google's native host.
            if self.google_api_keys and self.a6api_api_key:
                a6_base_url = (
                    os.environ.get("GEMINI_A6API_BASE_URL")
                    or os.environ.get("GEMINI_BASE_URL")
                    or ""
                ).strip().rstrip("/")
                try:
                    self.client = self._client_for(self.a6api_api_key, a6_base_url)
                    for model in self.models:
                        text = self._generate_text_once(
                            prompt, model=model, include_timeout=True
                        )
                        if text:
                            return text
                except Exception as exc:
                    last_exc = exc
            _obs["outcome"] = "error"
            _obs["error_category"] = "dependency"
            if last_exc is not None:
                self.logger.warning("Gemini generate exhausted all models: %s", type(last_exc).__name__)
            return ""

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
        if not self.client:
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
        text = self._generate_text(prompt)
        if not text:
            return fallback

        payload = self._extract_json_object(text)
        if not payload:
            return {"explanation": text, "pros": reasons, "cons": []}
        try:
            parsed = json.loads(payload)
            if not isinstance(parsed, dict):
                return fallback
            return {
                "explanation": str(parsed.get("explanation", fallback["explanation"])),
                "pros": list(parsed.get("pros", reasons))[:5],
                "cons": list(parsed.get("cons", []))[:5],
            }
        except Exception:
            return fallback

    def extract_property(self, blob: str) -> Dict[str, Any]:
        if not self.client:
            return {}
        prompt = (
            "Extract property fields into strict JSON. "
            "Keys: title,address,price,property_type,bedrooms,bathrooms,square_feet,description,status,"
            "year_built,parking_spaces,floors,units,property_condition,property_features,neighborhood,"
            "property_category,listing_type,rahn,ejare. Use null when unknown.\n"
            f"TEXT:\n{blob}"
        )
        text = self._generate_text(prompt)
        if not text:
            return {}
        payload = self._extract_json_object(text)
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _smart_context_fallback(self, property_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        property_data = property_data or {}
        property_id = property_data.get("property_id") or property_data.get("id") or ""
        return {
            "property_id": str(property_id),
            "smart_benefits": [{"benefit": "Great potential."}],
            "trending_badges": [],
        }

    def _normalize_smart_context_payload(
        self,
        payload: Dict[str, Any],
        fallback: Dict[str, Any],
    ) -> Dict[str, Any]:
        smart_benefits: List[Dict[str, str]] = []
        for item in payload.get("smart_benefits", []):
            if isinstance(item, dict):
                benefit = str(item.get("benefit") or "").strip()
                feature = str(item.get("feature") or "").strip()
                if not benefit:
                    continue
                row: Dict[str, str] = {"benefit": benefit}
                if feature:
                    row["feature"] = feature
                smart_benefits.append(row)
            elif isinstance(item, str):
                benefit = item.strip()
                if benefit:
                    smart_benefits.append({"benefit": benefit})

        trending_badges = []
        for badge in payload.get("trending_badges", []):
            badge_text = str(badge or "").strip()
            if badge_text:
                trending_badges.append(badge_text)

        if not smart_benefits:
            smart_benefits = list(fallback["smart_benefits"])

        property_id = str(payload.get("property_id") or fallback.get("property_id") or "")
        return {
            "property_id": property_id,
            "smart_benefits": smart_benefits[:5],
            "trending_badges": trending_badges[:5],
        }

    def analyze_multimodal_context(
        self,
        property_data: Dict[str, Any],
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Generate deterministic smart-context JSON for a property.
        Returns a hard fallback on any provider/timeout/parsing failure.
        """
        fallback = self._smart_context_fallback(property_data)
        if not self.client:
            return fallback

        prompt = (
            "Return ONLY JSON with keys property_id, smart_benefits, trending_badges.\n"
            "smart_benefits must be an array of objects with keys feature and benefit.\n"
            "Write short silver-lining lifestyle benefits for drawbacks.\n"
            "trending_badges must be an array of short strings.\n"
            f"Property input: {json.dumps(property_data, ensure_ascii=False)}"
        )

        try:
            from google.genai import types

            parts = [types.Part(text=prompt)]
            if image_bytes:
                parts.append(
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=mime_type or "image/jpeg",
                            data=image_bytes,
                        )
                    )
                )
            content = types.Content(parts=parts)

            text = ""
            for model in self.models:
                kwargs: Dict[str, Any] = {
                    "model": model,
                    "contents": [content],
                    "config": {"response_mime_type": "application/json"},
                }
                if self.request_timeout_seconds > 0:
                    kwargs["request_options"] = {"timeout": self.request_timeout_seconds}
                try:
                    try:
                        response = self.client.models.generate_content(**kwargs)
                    except TypeError:
                        kwargs.pop("request_options", None)
                        try:
                            response = self.client.models.generate_content(**kwargs)
                        except TypeError:
                            kwargs.pop("config", None)
                            response = self.client.models.generate_content(**kwargs)
                    text = getattr(response, "text", None) or ""
                    if text:
                        break
                except Exception as model_exc:
                    msg = str(model_exc)
                    if any(x in msg for x in ("404", "NOT_FOUND", "429", "RESOURCE_EXHAUSTED", "no longer available")):
                        self.logger.warning(
                            "Gemini smart-context model %s failed (%s); trying next",
                            model,
                            type(model_exc).__name__,
                        )
                        continue
                    raise

            payload_str = self._extract_json_object(text) or text
            parsed = json.loads(payload_str) if payload_str else {}
            if not isinstance(parsed, dict):
                return fallback

            return self._normalize_smart_context_payload(parsed, fallback)
        except Exception as exc:
            self.logger.warning("Gemini smart-context analysis failed; using fallback: %s", exc)
            return fallback

    def extract_property_from_image(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        if not self.client:
            return {}
        
        prompt = (
            "Analyze this real estate image (flyer or description) and extract property details into strict JSON. "
            "Keys: title,address,price,property_type,bedrooms,bathrooms,square_feet,description,status,"
            "year_built,parking_spaces,floors,units,property_condition,property_features,neighborhood,"
            "property_category,listing_type,rahn,ejare. Use null when unknown."
        )

        try:
            from google.genai import types
            
            # Create content with text prompt and image blob
            content = types.Content(
                parts=[
                    types.Part(text=prompt),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=mime_type,
                            data=image_bytes
                        )
                    )
                ]
            )

            text = ""
            for model in self.models:
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=[content],
                    )
                    text = getattr(response, "text", None) or ""
                    if text:
                        break
                except Exception as model_exc:
                    msg = str(model_exc)
                    if any(x in msg for x in ("404", "NOT_FOUND", "429", "RESOURCE_EXHAUSTED", "no longer available")):
                        self.logger.warning(
                            "Gemini image model %s failed (%s); trying next",
                            model,
                            type(model_exc).__name__,
                        )
                        continue
                    raise

            if not text:
                return {}

            payload = self._extract_json_object(text)
            if not payload:
                return {}

            parsed = json.loads(payload)
            if not isinstance(parsed, dict):
                return {}

            smart_context = self.analyze_multimodal_context(
                property_data=parsed,
                image_bytes=image_bytes,
                mime_type=mime_type,
            )
            parsed["smart_benefits"] = smart_context.get("smart_benefits", [])
            parsed["trending_badges"] = smart_context.get("trending_badges", [])
            return parsed
        except Exception as exc:
            self.logger.warning(f"Gemini image extraction failed: {exc}")
            return {}

    def extract_customer(self, blob: str) -> Dict[str, Any]:
        if not self.client:
            return {}
        prompt = (
            "Extract customer fields into strict JSON. "
            "Keys: name,email,phone,preferences,budget_min,budget_max,desired_neighborhoods,"
            "desired_property_type,bedrooms_min,bathrooms_min. Use null when unknown.\n"
            f"TEXT:\n{blob}"
        )
        text = self._generate_text(prompt)
        if not text:
            return {}
        payload = self._extract_json_object(text)
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def generate_market_analysis(self, prompt: str) -> str:
        return self._generate_text(prompt)
