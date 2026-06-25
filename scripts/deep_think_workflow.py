#!/usr/bin/env python3
"""Generate and operate a Deep Think workflow for this repository.

This utility intentionally does not persist authentication cookies.
"""

from __future__ import annotations

import argparse
import json
import re
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEEP_THINK_DIR = PROJECT_ROOT / "deep_think"
PROMPTS_DIR = DEEP_THINK_DIR / "prompts"
RESPONSES_DIR = DEEP_THINK_DIR / "responses"
CONTEXT_MANIFEST_PATH = DEEP_THINK_DIR / "context_manifest.json"
PROMPT_CHAIN_PATH = DEEP_THINK_DIR / "prompt_chain.json"
SESSION_PATH = DEEP_THINK_DIR / "deep_think_session.md"
BACKLOG_JSON_PATH = DEEP_THINK_DIR / "implementation_backlog.json"
BACKLOG_MD_PATH = DEEP_THINK_DIR / "implementation_backlog.md"

TESTSPRITE_REPORT_PATH = PROJECT_ROOT / "testsprite_tests" / "tmp" / "report_prompt.json"

FOCUS_FAILURE_IDS = {
    "TC001",
    "TC003",
    "TC004",
    "TC005",
    "TC007",
    "TC009",
    "TC010",
    "TC012",
    "TC013",
    "TC014",
}


@dataclass(frozen=True)
class ChunkSpec:
    chunk_id: str
    file: str
    reason: str
    anchor_pattern: str
    before: int
    after: int
    fallback: Tuple[int, int]


CONTEXT_SPECS: List[ChunkSpec] = [
    ChunkSpec(
        chunk_id="CTX-001",
        file="app.py",
        reason="Default-deny auth middleware, request classification, and redirect/401 behavior.",
        anchor_pattern=r"def register_auth_middleware",
        before=5,
        after=90,
        fallback=(1, 140),
    ),
    ChunkSpec(
        chunk_id="CTX-002",
        file="app.py",
        reason="CSRF/session configuration and secret handling, including defaults.",
        anchor_pattern=r"flask_app\.config\[\"WTF_CSRF_ENABLED\"\]",
        before=25,
        after=60,
        fallback=(90, 230),
    ),
    ChunkSpec(
        chunk_id="CTX-003",
        file="views/main.py",
        reason="Recommendations flow and fallback behavior when Gemini fails.",
        anchor_pattern=r"def get_customer_recommendations",
        before=15,
        after=120,
        fallback=(300, 440),
    ),
    ChunkSpec(
        chunk_id="CTX-004",
        file="views/main.py",
        reason="Recommendations export path (PDF/Excel/JSON) and error/redirect behavior.",
        anchor_pattern=r"def export_recommendations",
        before=10,
        after=120,
        fallback=(430, 620),
    ),
    ChunkSpec(
        chunk_id="CTX-005",
        file="views/properties.py",
        reason="Property modal/detail/edit endpoints and compatibility route contracts.",
        anchor_pattern=r"def view_property\(",
        before=10,
        after=300,
        fallback=(520, 830),
    ),
    ChunkSpec(
        chunk_id="CTX-006",
        file="static/js/main.js",
        reason="Modal manager and share/view UI flow where modal wiring issues were observed.",
        anchor_pattern=r"class PropertyModalManager",
        before=20,
        after=260,
        fallback=(760, 1225),
    ),
    ChunkSpec(
        chunk_id="CTX-007",
        file="static/js/crud-utils.js",
        reason="CRUD utility behaviors for form submission, toast feedback, and CSRF headers.",
        anchor_pattern=r"class CRUDUtils",
        before=0,
        after=240,
        fallback=(1, 260),
    ),
    ChunkSpec(
        chunk_id="CTX-008",
        file="services/gemini_service.py",
        reason="Recommendation generation and deterministic fallback flow.",
        anchor_pattern=r"def get_property_recommendations",
        before=20,
        after=190,
        fallback=(120, 320),
    ),
    ChunkSpec(
        chunk_id="CTX-009",
        file="services/llm/providers/gemini_provider.py",
        reason="Provider-level generation, availability checks, and JSON parsing behavior.",
        anchor_pattern=r"class GeminiProvider",
        before=0,
        after=220,
        fallback=(1, 220),
    ),
    ChunkSpec(
        chunk_id="CTX-010",
        file="services/vector_service.py",
        reason="Hybrid semantic/rule scoring and fallback search mechanics.",
        anchor_pattern=r"def search_properties",
        before=10,
        after=210,
        fallback=(250, 470),
    ),
    ChunkSpec(
        chunk_id="CTX-011",
        file="services/search_service.py",
        reason="RRF hybrid search orchestration joining semantic and keyword retrieval.",
        anchor_pattern=r"class SearchService",
        before=0,
        after=220,
        fallback=(1, 220),
    ),
]


STAGE_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "id": "P1",
        "objective": "Critical-path triage",
        "context_ids": ["CTX-003", "CTX-005", "CTX-006", "CTX-007", "CTX-012"],
        "expected_output": "ranked_fix_plan",
        "question": (
            "Given these failures, what is the minimum dependency-ordered fix sequence to "
            "restore all critical CRUD and modal flows without regressions?"
        ),
        "required_format": [
            "Priority table with top 5 blockers",
            "Dependency ordering and minimal patch strategy",
            "Concrete affected files per blocker",
            "At least one regression test per blocker",
        ],
    },
    {
        "id": "P2",
        "objective": "Frontend failure root-cause",
        "context_ids": ["CTX-005", "CTX-006", "CTX-007", "CTX-012"],
        "expected_output": "root_cause_map_and_fix_sequence",
        "question": (
            "What single root cause could explain CRUD/modal regressions (misrouted modals, "
            "symbol collisions, blank quick/full details, export toast failures), and what is "
            "the exact code-level remediation sequence?"
        ),
        "required_format": [
            "Root-cause map with evidence",
            "Step-by-step remediation sequence",
            "Patch-order rationale",
            "Verification checklist",
        ],
    },
    {
        "id": "P3",
        "objective": "Security and auth hardening",
        "context_ids": ["CTX-001", "CTX-002", "CTX-003", "CTX-007", "CTX-012"],
        "expected_output": "threat_fix_matrix",
        "question": (
            "How should auth middleware and CSRF/session settings be revised so UI flows remain "
            "usable while API/admin paths stay secure?"
        ),
        "required_format": [
            "Threat -> fix matrix",
            "Exact route/middleware implications",
            "Cookie/session hardening recommendations",
            "Regression tests for CSRF/auth/session behavior",
        ],
    },
    {
        "id": "P4",
        "objective": "AI recommendation reliability",
        "context_ids": ["CTX-003", "CTX-008", "CTX-009", "CTX-010", "CTX-011", "CTX-012"],
        "expected_output": "fallback_decision_tree",
        "question": (
            "What fallback contract should recommendations follow when Gemini is unavailable to "
            "avoid redirects/401 loops and still deliver useful output?"
        ),
        "required_format": [
            "Decision tree for success/failure paths",
            "Deterministic fallback ranking behavior",
            "User-facing error-state UX contract",
            "Acceptance criteria and failure-mode tests",
        ],
    },
    {
        "id": "P5",
        "objective": "Execution synthesis",
        "context_ids": [
            "CTX-001",
            "CTX-002",
            "CTX-003",
            "CTX-004",
            "CTX-005",
            "CTX-006",
            "CTX-007",
            "CTX-008",
            "CTX-009",
            "CTX-010",
            "CTX-011",
            "CTX-012",
        ],
        "expected_output": "three_wave_execution_backlog",
        "question": (
            "Propose a 3-wave implementation plan with explicit files, tests, and rollback checks "
            "for each wave."
        ),
        "required_format": [
            "Wave 1/2/3 with dependency order",
            "File-level tasks and risk tags",
            "Rollback checks",
            "Unit/integration/e2e test plan",
        ],
    },
]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_directories() -> None:
    DEEP_THINK_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_lines(path: Path) -> List[str]:
    return read_text(path).splitlines()


def clamp_range(start: int, end: int, total: int) -> Tuple[int, int]:
    safe_start = max(1, min(start, total))
    safe_end = max(safe_start, min(end, total))
    return safe_start, safe_end


def find_anchor_line(lines: List[str], pattern: str) -> int | None:
    compiled = re.compile(pattern)
    for idx, line in enumerate(lines, start=1):
        if compiled.search(line):
            return idx
    return None


def sanitize_excerpt(text: str) -> str:
    redacted = text
    patterns = [
        (r"(?i)(api[_-]?key\s*[:=]\s*[\"'])([^\"']+)([\"'])", r"\1<REDACTED>\3"),
        (r"(?i)(secret\s*[:=]\s*[\"'])([^\"']+)([\"'])", r"\1<REDACTED>\3"),
        (r"(?i)(token\s*[:=]\s*[\"'])([^\"']+)([\"'])", r"\1<REDACTED>\3"),
        (r"(?i)(password\s*[:=]\s*[\"'])([^\"']+)([\"'])", r"\1<REDACTED>\3"),
    ]
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted


def build_chunk(spec: ChunkSpec) -> Dict[str, Any]:
    path = PROJECT_ROOT / spec.file
    lines = read_lines(path)
    total = len(lines)
    anchor = find_anchor_line(lines, spec.anchor_pattern)
    if anchor is None:
        start, end = clamp_range(spec.fallback[0], spec.fallback[1], total)
    else:
        start, end = clamp_range(anchor - spec.before, anchor + spec.after, total)
    excerpt = "\n".join(lines[start - 1 : end])
    excerpt = sanitize_excerpt(excerpt)
    return {
        "id": spec.chunk_id,
        "file": spec.file,
        "start_line": start,
        "end_line": end,
        "reason": spec.reason,
        "excerpt": excerpt,
    }


def load_failure_records() -> List[Dict[str, Any]]:
    if not TESTSPRITE_REPORT_PATH.exists():
        return []
    payload = json.loads(read_text(TESTSPRITE_REPORT_PATH))
    test_result = (
        payload.get("next_action", [{}])[0]
        .get("input", {})
        .get("testResult", [])
    )
    failures: List[Dict[str, Any]] = []
    for item in test_result:
        test_id = item.get("testCaseId")
        if test_id not in FOCUS_FAILURE_IDS:
            continue
        failure_reason = str(item.get("failureReason") or "").strip()
        summary = failure_reason.split(".")[0].strip() if failure_reason else "No summary provided"
        failures.append(
            {
                "source": str(TESTSPRITE_REPORT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "test_id": test_id,
                "severity": item.get("severity", "Unknown"),
                "summary": summary,
                "component": item.get("component", "Unknown"),
                "recommendation": item.get("recommendation", ""),
            }
        )
    return failures


def build_failure_chunk(failures: List[Dict[str, Any]]) -> Dict[str, Any]:
    source_rel = str(TESTSPRITE_REPORT_PATH.relative_to(PROJECT_ROOT)).replace("\\", "/")
    lines = read_lines(TESTSPRITE_REPORT_PATH) if TESTSPRITE_REPORT_PATH.exists() else []
    line_hits = []
    for idx, line in enumerate(lines, start=1):
        for failure in failures:
            if f"\"testCaseId\": \"{failure['test_id']}\"" in line:
                line_hits.append(idx)
                break
    if line_hits:
        start, end = clamp_range(min(line_hits) - 3, max(line_hits) + 20, len(lines))
    else:
        start, end = (1, min(120, len(lines))) if lines else (1, 1)

    summary_lines = []
    for failure in failures:
        summary_lines.append(
            f"- {failure['test_id']} [{failure['severity']}]: {failure['summary']} "
            f"(component: {failure['component']})"
        )
    excerpt = "\n".join(summary_lines) if summary_lines else "No focused failure records found."
    return {
        "id": "CTX-012",
        "file": source_rel,
        "start_line": start,
        "end_line": end,
        "reason": "High-severity frontend/auth/recommendation failures from automated UI validation.",
        "excerpt": sanitize_excerpt(excerpt),
    }


def build_context_manifest() -> Dict[str, Any]:
    chunks = [build_chunk(spec) for spec in CONTEXT_SPECS]
    failures = load_failure_records()
    chunks.append(build_failure_chunk(failures))
    return {
        "project": PROJECT_ROOT.name,
        "generated_at": utc_now_iso(),
        "focus": "critical_path",
        "mode": "semi_automated",
        "cookie_handling": "in_memory_only",
        "chunks": chunks,
        "known_failures": failures,
    }


def build_prompt_chain() -> Dict[str, Any]:
    return {
        "project": PROJECT_ROOT.name,
        "generated_at": utc_now_iso(),
        "stages": STAGE_DEFINITIONS,
    }


def trim_excerpt(text: str, max_chars: int = 2800) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 28] + "\n...[TRUNCATED FOR PROMPT SIZE]"


def render_stage_prompt(stage: Dict[str, Any], context_by_id: Dict[str, Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append(f"# Deep Think Stage {stage['id']}: {stage['objective']}")
    lines.append("")
    lines.append("## Objective")
    lines.append(stage["objective"])
    lines.append("")
    lines.append("## Primary Question")
    lines.append(stage["question"])
    lines.append("")
    lines.append("## Required Output Format")
    for item in stage["required_format"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Context Chunks")
    for context_id in stage["context_ids"]:
        chunk = context_by_id.get(context_id)
        if not chunk:
            continue
        lines.append(f"### {context_id} - `{chunk['file']}`:{chunk['start_line']}")
        lines.append(f"Reason: {chunk['reason']}")
        lines.append("```text")
        lines.append(trim_excerpt(chunk["excerpt"]))
        lines.append("```")
        lines.append("")
    lines.append("## Response Constraints")
    lines.append("- Cite context chunk IDs for each major recommendation.")
    lines.append("- Keep recommendations implementation-oriented and dependency-ordered.")
    lines.append("- Include tests needed for every high-severity item.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_session_template(prompt_chain: Dict[str, Any]) -> str:
    lines = [
        "# Deep Think Session Log",
        "",
        "## Session Metadata",
        f"- project: `{prompt_chain['project']}`",
        f"- generated_at: `{utc_now_iso()}`",
        "- mode: `semi-automated`",
        "- cookie_handling: `in-memory only`",
        "",
        "## Operator Workflow",
        "1. Open Gemini with MCP Playwright and inject cookies in-memory only.",
        "2. Submit stage prompt from `deep_think/prompts/<stage>.md`.",
        "3. Wait for full answer (Deep Think can be slow).",
        "4. Append response using this script (`append-response`).",
        "5. Build backlog using this script (`build-backlog`).",
        "",
    ]
    for stage in prompt_chain["stages"]:
        lines.extend(
            [
                f"## Stage {stage['id']} - {stage['objective']}",
                f"- prompt_file: `deep_think/prompts/{stage['id']}.md`",
                "- submitted_at: `TBD`",
                "- response_link: `TBD`",
                "",
                "### Response Summary",
                "TBD",
                "",
                "### Actionable Decisions",
                "TBD",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def command_generate(_: argparse.Namespace) -> None:
    ensure_directories()
    manifest = build_context_manifest()
    prompt_chain = build_prompt_chain()
    context_by_id = {chunk["id"]: chunk for chunk in manifest["chunks"]}

    write_json(CONTEXT_MANIFEST_PATH, manifest)
    write_json(PROMPT_CHAIN_PATH, prompt_chain)
    write_text(SESSION_PATH, render_session_template(prompt_chain))

    for stage in prompt_chain["stages"]:
        stage_prompt_path = PROMPTS_DIR / f"{stage['id']}.md"
        write_text(stage_prompt_path, render_stage_prompt(stage, context_by_id))

    print("Generated Deep Think artifacts:")
    print(f"- {CONTEXT_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    print(f"- {PROMPT_CHAIN_PATH.relative_to(PROJECT_ROOT)}")
    print(f"- {SESSION_PATH.relative_to(PROJECT_ROOT)}")
    for stage in prompt_chain["stages"]:
        stage_prompt = PROMPTS_DIR / f"{stage['id']}.md"
        print(f"- {stage_prompt.relative_to(PROJECT_ROOT)}")


def read_prompt_chain() -> Dict[str, Any]:
    if not PROMPT_CHAIN_PATH.exists():
        raise FileNotFoundError("prompt_chain.json not found. Run the generate command first.")
    return json.loads(read_text(PROMPT_CHAIN_PATH))


def stage_exists(stage_id: str, prompt_chain: Dict[str, Any]) -> bool:
    return any(stage.get("id") == stage_id for stage in prompt_chain.get("stages", []))


def parse_paths(text: str) -> List[str]:
    pattern = re.compile(
        r"(?:[A-Za-z0-9_\-./]+(?:\.py|\.js|\.html|\.css|\.json|\.md)|"
        r"(?:views|services|static|templates|tests|scripts)/[A-Za-z0-9_\-./]+)"
    )
    found = pattern.findall(text)
    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for item in found:
        normalized = item.strip().strip("`")
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def parse_response_to_items(stage_id: str, text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines:
        if line.startswith("#"):
            continue
        priority_match = re.search(r"\b(P0|P1|P2)\b", line, flags=re.IGNORECASE)
        if not priority_match:
            continue
        priority = priority_match.group(1).upper()
        change_scope = parse_paths(line)
        if not change_scope:
            continue
        risk = "regression"
        lowered = line.lower()
        if any(k in lowered for k in ["csrf", "auth", "session", "xss", "security"]):
            risk = "security"
        elif any(k in lowered for k in ["db", "migration", "schema", "data"]):
            risk = "data"

        tests_needed: List[str] = []
        if "unit" in lowered:
            tests_needed.append("unit")
        if "integration" in lowered:
            tests_needed.append("integration")
        if "e2e" in lowered or "playwright" in lowered:
            tests_needed.append("e2e")
        if not tests_needed:
            tests_needed = ["integration"]

        items.append(
            {
                "stage": stage_id,
                "priority": priority,
                "summary": line[:280],
                "change_scope": change_scope,
                "risk": risk,
                "tests_needed": tests_needed,
            }
        )
    return items


def append_to_session(
    stage_id: str,
    response_text: str,
    response_link: str | None,
) -> Path:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    response_path = RESPONSES_DIR / f"{stage_id}_{timestamp}.md"
    write_text(response_path, response_text.rstrip() + "\n")

    section = [
        f"\n## Captured Response {stage_id} @ {timestamp}",
        f"- response_file: `{response_path.relative_to(PROJECT_ROOT)}`",
        f"- response_link: `{response_link or 'N/A'}`",
        "",
        "```text",
        trim_excerpt(response_text, max_chars=3000),
        "```",
        "",
    ]
    if not SESSION_PATH.exists():
        write_text(SESSION_PATH, "# Deep Think Session Log\n")
    with SESSION_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(section))

    return response_path


def command_append_response(args: argparse.Namespace) -> None:
    ensure_directories()
    prompt_chain = read_prompt_chain()
    stage_id = args.stage.strip().upper()
    if not stage_exists(stage_id, prompt_chain):
        raise ValueError(f"Unknown stage '{stage_id}'.")

    if args.response_file:
        response_text = read_text(Path(args.response_file))
    else:
        response_text = args.response_text or ""
    response_text = response_text.strip()
    if not response_text:
        raise ValueError("Response text is empty. Provide --response-file or --response-text.")

    response_path = append_to_session(stage_id, response_text, args.response_link)
    print(f"Captured response at {response_path.relative_to(PROJECT_ROOT)}")


def iter_response_files() -> Iterable[Path]:
    if not RESPONSES_DIR.exists():
        return []
    # Only parse timestamped captured responses (e.g. P3_20260218T215248Z.md).
    # Excludes helper notes like P3_manual_summary.md to avoid duplicates.
    return sorted(RESPONSES_DIR.glob("P[1-5]_20*.md"))


def command_build_backlog(_: argparse.Namespace) -> None:
    ensure_directories()
    all_items: List[Dict[str, Any]] = []
    response_sources: List[str] = []
    for path in iter_response_files():
        response_sources.append(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
        text = read_text(path)
        stage_id = path.stem.split("_", 1)[0]
        all_items.extend(parse_response_to_items(stage_id, text))

    payload = {
        "project": PROJECT_ROOT.name,
        "generated_at": utc_now_iso(),
        "sources": response_sources,
        "items": all_items,
    }
    write_json(BACKLOG_JSON_PATH, payload)

    md_lines = [
        "# Implementation Backlog (Derived from Deep Think Responses)",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- sources: `{len(response_sources)}`",
        f"- parsed_items: `{len(all_items)}`",
        "",
        "| Priority | Stage | Risk | Summary | Change Scope | Tests Needed |",
        "|---|---|---|---|---|---|",
    ]
    for item in all_items:
        scope = ", ".join(item["change_scope"]) if item["change_scope"] else "TBD"
        tests = ", ".join(item["tests_needed"])
        summary = item["summary"].replace("|", "\\|")
        md_lines.append(
            f"| {item['priority']} | {item['stage']} | {item['risk']} | {summary} | "
            f"{scope} | {tests} |"
        )
    if not all_items:
        md_lines.append("| N/A | N/A | N/A | No structured lines containing P0/P1/P2 were found. | TBD | TBD |")

    md_lines.extend(
        [
            "",
            "## Acceptance Checks",
            "- Every high-severity failure should map to at least one backlog item.",
            "- Wave ordering should remain dependency-ordered.",
            "- Each P0/P1 item should include at least one regression test.",
            "",
        ]
    )
    write_text(BACKLOG_MD_PATH, "\n".join(md_lines))

    print("Backlog artifacts written:")
    print(f"- {BACKLOG_JSON_PATH.relative_to(PROJECT_ROOT)}")
    print(f"- {BACKLOG_MD_PATH.relative_to(PROJECT_ROOT)}")


def normalize_cookie(cookie: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {
        "name": cookie["name"],
        "value": cookie["value"],
        "domain": cookie["domain"],
        "path": cookie.get("path", "/"),
        "httpOnly": bool(cookie.get("httpOnly", False)),
        "secure": bool(cookie.get("secure", False)),
    }
    expiration = cookie.get("expirationDate")
    if expiration:
        normalized["expires"] = int(float(expiration))

    raw_same_site = cookie.get("sameSite")
    if isinstance(raw_same_site, str):
        lowered = raw_same_site.lower()
        if lowered == "no_restriction":
            normalized["sameSite"] = "None"
        elif lowered == "lax":
            normalized["sameSite"] = "Lax"
        elif lowered == "strict":
            normalized["sameSite"] = "Strict"
    return normalized


def command_emit_cookie_js(args: argparse.Namespace) -> None:
    raw = json.loads(read_text(Path(args.cookies_file)))
    if not isinstance(raw, list):
        raise ValueError("Cookie JSON must be a list.")
    normalized = [normalize_cookie(item) for item in raw]
    js = textwrap.dedent(
        f"""\
        async (page) => {{
          const cookies = {json.dumps(normalized, ensure_ascii=False, indent=2)};
          await page.context().addCookies(cookies);
          await page.goto("https://gemini.google.com/app", {{ waitUntil: "domcontentloaded" }});
          return {{ url: page.url(), cookieCount: cookies.length }};
        }}
        """
    ).strip()
    print(js)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deep Think workflow utility.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate workflow artifacts.")
    generate.set_defaults(func=command_generate)

    append_response = subparsers.add_parser("append-response", help="Append stage response to session log.")
    append_response.add_argument("--stage", required=True, help="Stage ID (P1..P5).")
    append_response.add_argument("--response-file", help="Path to captured Gemini response markdown/text.")
    append_response.add_argument("--response-text", help="Inline response text.")
    append_response.add_argument("--response-link", help="Optional Gemini shared link.")
    append_response.set_defaults(func=command_append_response)

    build_backlog = subparsers.add_parser("build-backlog", help="Build implementation backlog from responses.")
    build_backlog.set_defaults(func=command_build_backlog)

    emit_cookie_js = subparsers.add_parser(
        "emit-cookie-js",
        help="Emit Playwright MCP run_code snippet with normalized cookies. Do not commit cookie files.",
    )
    emit_cookie_js.add_argument("--cookies-file", required=True, help="Path to input cookie JSON file.")
    emit_cookie_js.set_defaults(func=command_emit_cookie_js)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
