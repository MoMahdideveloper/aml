#!/usr/bin/env python
"""Provider smoke gate for AI form assist.

Usage
-----
Mock mode (no credentials, no network, no DB — safe for CI):
    python scripts/verify_ai_form_provider.py --mode mock

Live mode (requires AI_FORM_LIVE_SMOKE=1 and configured provider credentials):
    AI_FORM_LIVE_SMOKE=1 python scripts/verify_ai_form_provider.py --mode live

Exit codes
----------
0  All checks passed.
1  One or more checks failed, or a required guard condition was not met.

Output
------
Sanitized JSON summary on stdout.  Diagnostic messages on stderr.
No prompts, no media blobs, no extracted sensitive values, no keys.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Ensure project root is importable when run as a script
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Synthetic fixtures — generated in memory, never persisted
# ---------------------------------------------------------------------------

# Synthetic Persian property listing text (no real PII, no real addresses)
_SYNTHETIC_PERSIAN_TEXT = (
    "عنوان: آپارتمان نمونه در منطقه آزمایشی\n"
    "آدرس: خیابان تست، پلاک ۰، واحد آزمایشی\n"
    "محله: محله_آزمایش\n"
    "۳ خواب، ۲ حمام، ۱۲۰ متر\n"
    "قیمت: ۵۰۰۰۰۰ تومان\n"
    "توضیحات: این یک متن آزمایشی برای دود تست است."
)

# Synthetic small PNG (1×1 white pixel) — generated in memory, never written to disk
_SYNTHETIC_PNG_1X1 = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR length + type
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # 8-bit RGB + CRC
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
    0x00, 0x05, 0xFE, 0x02, 0xFE, 0xA8, 0xE8, 0x45,
    0x81, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND
    0x44, 0xAE, 0x42, 0x60, 0x82,
])

# Synthetic minimal WAV silence (44-byte header + 0 samples)
def _synthetic_wav() -> bytes:
    import struct
    num_samples = 0
    data_size = num_samples * 2
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, 16000, 32000, 2, 16,
        b"data", data_size,
    )


# ---------------------------------------------------------------------------
# Individual check helpers
# ---------------------------------------------------------------------------

CheckResult = Dict[str, Any]


def _check(name: str, ok: bool, detail: str = "") -> CheckResult:
    return {"name": name, "ok": ok, "detail": detail}


def _check_schema_registry() -> CheckResult:
    """Verify the schema registry loads all expected form names (symmetric check)."""
    try:
        from services.ai_form_assist.schema_registry import list_form_schemas, get_form_schema

        schemas = list_form_schemas()
        schema_set = set(schemas)
        expected = {"property", "customer", "recommendation", "deal", "task", "agent"}
        missing = expected - schema_set
        extra = schema_set - expected
        if missing:
            return _check("schema_registry", False, f"Missing schemas: {sorted(missing)}")
        if extra:
            return _check(
                "schema_registry",
                False,
                f"Unexpected extra schemas: {sorted(extra)} — update expected set",
            )
        # Spot-check one schema round-trip
        prop = get_form_schema("property")
        if "title" not in prop.fields:
            return _check("schema_registry", False, "property schema missing 'title' field")
        return _check("schema_registry", True, f"all {len(schemas)} schemas present")
    except Exception as exc:
        return _check("schema_registry", False, f"{type(exc).__name__}: {exc}")


def _check_form_schemas_valid() -> CheckResult:
    """Validate that every registered form schema has at least one field."""
    try:
        from services.ai_form_assist.schema_registry import list_form_schemas, get_form_schema

        for name in list_form_schemas():
            schema = get_form_schema(name)
            if not schema.fields:
                return _check("form_schemas_valid", False, f"'{name}' has no fields")
        return _check("form_schemas_valid", True, "all form schemas non-empty")
    except Exception as exc:
        return _check("form_schemas_valid", False, f"{type(exc).__name__}: {exc}")


def _check_text_extraction_mock() -> CheckResult:
    """Extract from synthetic Persian text using mock extractor, check output shape."""
    try:
        from services.ai_form_assist.mock_extractor import mock_extract

        result = mock_extract(form="property", text=_SYNTHETIC_PERSIAN_TEXT)
        if result.degraded:
            return _check("text_extraction_mock", False, f"degraded: {result.error}")
        if not result.suggestions:
            return _check("text_extraction_mock", False, "no suggestions returned")
        field_names = [s.field for s in result.suggestions]
        if "title" not in field_names:
            return _check("text_extraction_mock", False, f"'title' missing. Got: {field_names}")
        # Sanitized: report only count + field names, never values
        return _check(
            "text_extraction_mock",
            True,
            f"{len(result.suggestions)} suggestions: {field_names}",
        )
    except Exception as exc:
        return _check("text_extraction_mock", False, f"{type(exc).__name__}: {exc}")


def _check_image_fixture_mock() -> CheckResult:
    """Pass a synthetic in-memory image bytes to mock extractor; verify output."""
    try:
        from services.ai_form_assist.mock_extractor import mock_extract

        image_fixture: List[Tuple[bytes, str]] = [(_SYNTHETIC_PNG_1X1, "image/png")]
        result = mock_extract(form="property", text="", image_parts=image_fixture)
        if result.degraded:
            return _check("image_fixture_mock", False, f"degraded: {result.error}")
        if result.source_type.value not in ("image", "mixed"):
            return _check(
                "image_fixture_mock",
                False,
                f"unexpected source_type: {result.source_type}",
            )
        return _check("image_fixture_mock", True, f"source_type={result.source_type.value}")
    except Exception as exc:
        return _check("image_fixture_mock", False, f"{type(exc).__name__}: {exc}")


def _check_audio_fixture_mock() -> CheckResult:
    """Pass a synthetic in-memory audio bytes to mock extractor; verify output."""
    try:
        from services.ai_form_assist.mock_extractor import mock_extract

        audio_fixture: List[Tuple[bytes, str]] = [(_synthetic_wav(), "audio/wav")]
        result = mock_extract(form="property", text="", audio_parts=audio_fixture)
        if result.degraded:
            return _check("audio_fixture_mock", False, f"degraded: {result.error}")
        if result.source_type.value not in ("audio", "mixed"):
            return _check(
                "audio_fixture_mock",
                False,
                f"unexpected source_type: {result.source_type}",
            )
        return _check("audio_fixture_mock", True, f"source_type={result.source_type.value}")
    except Exception as exc:
        return _check("audio_fixture_mock", False, f"{type(exc).__name__}: {exc}")


def _check_extractor_unavailable_degrades() -> CheckResult:
    """GeminiFormExtractor with no client must degrade, not raise."""
    try:
        from services.ai_form_assist.gemini_extractor import GeminiFormExtractor

        ext = GeminiFormExtractor(client=None)
        result = ext.extract(form="property", text="test")
        if not result.degraded:
            return _check(
                "extractor_unavailable_degrades",
                False,
                "expected degraded=True with no client",
            )
        return _check("extractor_unavailable_degrades", True, "degraded correctly")
    except Exception as exc:
        return _check("extractor_unavailable_degrades", False, f"{type(exc).__name__}: {exc}")


def _check_extraction_result_schema() -> CheckResult:
    """ExtractionResult from mock must satisfy the type contract."""
    try:
        from services.ai_form_assist.mock_extractor import mock_extract
        from services.ai_form_assist.types import ExtractionResult

        result = mock_extract(form="customer", text="نام: مشتری_آزمایشی")
        if not isinstance(result, ExtractionResult):
            return _check("extraction_result_schema", False, "not an ExtractionResult instance")
        # Validate required fields without leaking values
        if result.form != "customer":
            return _check("extraction_result_schema", False, f"form mismatch: {result.form}")
        if not isinstance(result.suggestions, list):
            return _check("extraction_result_schema", False, "suggestions not a list")
        return _check("extraction_result_schema", True, "ExtractionResult contract satisfied")
    except Exception as exc:
        return _check("extraction_result_schema", False, f"{type(exc).__name__}: {exc}")


def _check_persian_text_fixture_customer() -> CheckResult:
    """Extract from a synthetic Persian customer note; verify field names only."""
    try:
        from services.ai_form_assist.mock_extractor import mock_extract

        text = (
            "نام: خریدار_آزمایشی\n"
            "بودجه: ۳۰۰۰۰۰ تومان\n"
            "۲ خواب\n"
            "محله: منطقه_آزمایش\n"
        )
        result = mock_extract(form="customer", text=text)
        if result.degraded:
            return _check("persian_text_customer", False, f"degraded: {result.error}")
        field_names = [s.field for s in result.suggestions]
        return _check("persian_text_customer", True, f"fields: {field_names}")
    except Exception as exc:
        return _check("persian_text_customer", False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Live-mode checks
# ---------------------------------------------------------------------------

def _check_live_credentials() -> CheckResult:
    """Verify at least one Gemini credential env var is set (non-empty)."""
    creds = {
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
    }
    configured = [k for k, v in creds.items() if v.strip()]
    if not configured:
        return _check("live_credentials", False, "No Gemini credentials configured")
    return _check("live_credentials", True, f"credential env vars present: {configured}")


def _check_live_extractor_available() -> CheckResult:
    """GeminiFormExtractor.is_available must be True for live smoke."""
    try:
        from services.ai_form_assist.gemini_extractor import GeminiFormExtractor

        ext = GeminiFormExtractor()
        if not ext.is_available:
            return _check("live_extractor_available", False, "GeminiFormExtractor.is_available=False")
        return _check("live_extractor_available", True, f"model={ext.fast_model}")
    except Exception as exc:
        return _check("live_extractor_available", False, f"{type(exc).__name__}: {exc}")


def _check_live_extraction() -> CheckResult:
    """Call live Gemini API with synthetic Persian text; validate output shape only."""
    try:
        from services.ai_form_assist.gemini_extractor import GeminiFormExtractor

        ext = GeminiFormExtractor()
        if not ext.is_available:
            return _check("live_extraction", False, "extractor unavailable")

        result = ext.extract(form="property", text=_SYNTHETIC_PERSIAN_TEXT)
        # Sanitized output: only report structure, never field values
        field_names = [s.field for s in result.suggestions]
        if result.degraded:
            return _check(
                "live_extraction",
                False,
                f"degraded={result.degraded} error={result.error}",
            )
        return _check(
            "live_extraction",
            True,
            f"model={result.model_id} suggestions={len(result.suggestions)} fields={field_names}",
        )
    except Exception as exc:
        return _check("live_extraction", False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Top-level runners
# ---------------------------------------------------------------------------

def run_mock() -> Dict[str, Any]:
    """Run the full mock smoke suite.  No credentials, no network, no DB writes."""
    t0 = time.monotonic()
    checks: List[CheckResult] = [
        _check_schema_registry(),
        _check_form_schemas_valid(),
        _check_text_extraction_mock(),
        _check_image_fixture_mock(),
        _check_audio_fixture_mock(),
        _check_extractor_unavailable_degrades(),
        _check_extraction_result_schema(),
        _check_persian_text_fixture_customer(),
    ]
    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    all_ok = all(c["ok"] for c in checks)
    return {
        "mode": "mock",
        "status": "pass" if all_ok else "fail",
        "checks": checks,
        "elapsed_ms": elapsed_ms,
    }


def run_live() -> Dict[str, Any]:
    """Run the live smoke suite.  Requires AI_FORM_LIVE_SMOKE=1 + credentials."""
    t0 = time.monotonic()
    cred_check = _check_live_credentials()
    avail_check = _check_live_extractor_available()
    checks: List[CheckResult] = [cred_check, avail_check]

    if cred_check["ok"] and avail_check["ok"]:
        checks.append(_check_live_extraction())

    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    all_ok = all(c["ok"] for c in checks)
    return {
        "mode": "live",
        "status": "pass" if all_ok else "fail",
        "checks": checks,
        "elapsed_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI form provider smoke gate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/verify_ai_form_provider.py --mode mock\n"
            "  AI_FORM_LIVE_SMOKE=1 python scripts/verify_ai_form_provider.py --mode live\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "live"],
        required=True,
        help="'mock' runs without credentials. 'live' requires AI_FORM_LIVE_SMOKE=1.",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.mode == "live":
        flag = os.environ.get("AI_FORM_LIVE_SMOKE", "").strip()
        if flag != "1":
            print(
                "ERROR: Live smoke requires AI_FORM_LIVE_SMOKE=1 to be set explicitly.\n"
                "This prevents accidental live API calls in CI or local dev.\n"
                "Set AI_FORM_LIVE_SMOKE=1 and ensure provider credentials are configured.",
                file=sys.stderr,
            )
            return 1
        summary = run_live()
    else:
        summary = run_mock()

    print(json.dumps(summary, indent=2))

    if summary["status"] != "pass":
        failed = [c for c in summary["checks"] if not c["ok"]]
        print(
            f"\nFAILED {len(failed)} check(s):",
            file=sys.stderr,
        )
        for c in failed:
            print(f"  - {c['name']}: {c.get('detail', '')}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
