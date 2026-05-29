"""Suppress placeholder/example secret pattern false positives."""

from __future__ import annotations

import re
from dataclasses import dataclass

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key_like", re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*[^\S\n]+")),
    ("jquants_key", re.compile(r"(?i)JQUANTS_API_KEY\s*=\s*[^\S\n]*")),
    ("alpha_vantage_key", re.compile(r"(?i)ALPHA_VANTAGE_API_KEY\s*=\s*[^\S\n]*")),
    ("gmail_token", re.compile(r"(?i)(GMAIL_|client_secret|refresh_token)")),
)

DOCUMENTATION_PATH_PREFIXES: tuple[str, ...] = (
    "docs/",
    "config/",
    "tests/",
)

TOOLING_PATH_PREFIXES: tuple[str, ...] = (
    "scripts/",
    "ops/",
)

SOURCE_CODE_PREFIXES: tuple[str, ...] = ("src/",)

DOCUMENTATION_EXACT_FILES: frozenset[str] = frozenset({".env.example"})

REPORTS_PRIVATE_SECURITY_MARKERS: frozenset[str] = frozenset(
    {
        "security",
        "leakage",
        "audit",
        "dashboard",
        "checklist",
        "evidence",
        "github_settings",
        "dependency_security",
    }
)

PLACEHOLDER_VALUE_RE = re.compile(
    r"(?i)^("
    r"your[_-]?|"
    r"placeholder|"
    r"example|"
    r"changeme|"
    r"redacted|"
    r"dummy|"
    r"test[_-]?key|"
    r"x{3,}|"
    r"<[^>]+>|"
    r"\*\*\*|"
    r"insert[_-]|"
    r"replace[_-]?me|"
    r"none|"
    r"null|"
    r"n/?a|"
    r"todo"
    r")",
)

REALISTIC_SECRET_VALUE_RE = re.compile(r"^[A-Za-z0-9+/=_-]{24,}$")

ENV_VAR_NAME_RE = re.compile(
    r"(?i)(JQUANTS_API_KEY|GMAIL_[A-Z0-9_]+|CONFIRM_GMAIL_SEND|ALPHA_VANTAGE_API_KEY|"
    r"refresh_token|client_secret|api[_-]?key)"
)

ENV_STYLE_ASSIGNMENT_RE = re.compile(r"^\s*(?:export\s+)?[A-Z][A-Z0-9_]*\s*=")


@dataclass(frozen=True)
class PatternHit:
    pattern_label: str
    line_number: int
    line_text: str


def collect_pattern_hits(
    *,
    rel_path: str,
    sample_text: str,
    patterns: tuple[tuple[str, re.Pattern[str]], ...] | None = None,
) -> list[PatternHit]:
    del rel_path
    use_patterns = patterns or SECRET_PATTERNS
    hits: list[PatternHit] = []
    for line_number, line in enumerate(sample_text.splitlines(), start=1):
        for label, pattern in use_patterns:
            if pattern.search(line):
                hits.append(PatternHit(pattern_label=label, line_number=line_number, line_text=line))
    return hits


def _assignment_value(line: str) -> str | None:
    if "=" not in line:
        return None
    return line.split("=", 1)[1].strip().strip("\"'").strip()


def value_looks_like_placeholder(value: str) -> bool:
    cleaned = value.strip().strip("\"'")
    if not cleaned:
        return True
    if PLACEHOLDER_VALUE_RE.match(cleaned):
        return True
    if cleaned.upper() in {"YOUR_API_KEY", "API_KEY", "SECRET", "TOKEN"}:
        return True
    return False


def value_looks_like_real_secret(value: str) -> bool:
    cleaned = value.strip().strip("\"'")
    if len(cleaned) < 24:
        return False
    if value_looks_like_placeholder(cleaned):
        return False
    return bool(REALISTIC_SECRET_VALUE_RE.match(cleaned))


def is_reports_private_redacted_path(rel_path: str) -> bool:
    lowered = rel_path.lower().replace("\\", "/")
    if lowered.startswith(("latest/", "weekly/")) or "/weekly/" in lowered:
        if lowered.endswith((".md", ".json", ".csv")) and "template" not in lowered:
            return True
    return any(marker in lowered for marker in REPORTS_PRIVATE_SECURITY_MARKERS)


def _line_clears_env_var(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("export "):
        return False
    assignments = re.findall(r"[A-Za-z0-9_]+\s*=\s*([^\\s#]*)", stripped)
    if not assignments:
        return False
    return all(value_looks_like_placeholder(val) or val == "" for val in assignments)


def _line_env_var_name_only(line: str) -> bool:
    stripped = line.strip()
    if ENV_STYLE_ASSIGNMENT_RE.match(stripped):
        value = _assignment_value(stripped)
        if value is not None and value_looks_like_real_secret(value):
            return False
        if value is not None:
            return value_looks_like_placeholder(value) or value == ""
    lower = stripped.lower()
    markers = (
        "getenv",
        "os.environ",
        "monkeypatch",
        "setenv",
        "delenv",
        "pytest",
        "help=",
        "typer.",
        "match=",
        "raises",
        "from_client_secrets",
        "api_key_present",
        "api_key_header",
        "api_key_value",
        "missing",
        "required",
        "never commit",
        "never performs",
        "do not",
        "checklist",
        "documentation",
        "example",
        "placeholder",
        "redacted",
        "dry-run",
        "dryrun",
        '"""',
        "''",
        "surfaced",
        "configured when",
        "legacy:",
        "gmail_failure",
        "gmail_delivery",
        "gmail_send",
        "gmail_oauth",
    )
    if any(m in lower for m in markers):
        return ENV_VAR_NAME_RE.search(stripped) is not None
    if stripped.startswith("#"):
        return ENV_VAR_NAME_RE.search(stripped) is not None
    return False


def classify_hit_category(
    *,
    rel_path: str,
    pattern_label: str,
    line: str,
    line_number: int,
) -> tuple[str, str, bool]:
    del line_number
    stripped = line.strip()
    if rel_path.endswith(".env") and not rel_path.endswith(".env.example"):
        return "real_secret_risk", "tracked_env_file", False

    if is_reports_private_redacted_path(rel_path):
        return "reports_private_redacted_reference", "reports_private_summary", True

    if rel_path.startswith("tests/"):
        if re.match(r"^\s*secret\s*=\s*[\"']", stripped, re.IGNORECASE):
            return "test_fixture", "test_secret_variable_setup", True
        if "monkeypatch.setenv" in stripped and "JQUANTS_API_KEY" in stripped:
            return "test_fixture", "test_env_injection", True
        if "JQUANTS_API_KEY={secret}" in stripped:
            return "test_fixture", "test_env_file_fixture", True
        if value_looks_like_real_secret(_assignment_value(line) or ""):
            return "real_secret_risk", "test_realistic_secret_shape", False
        if pattern_label == "gmail_token":
            return "test_fixture", "test_gmail_fixture", True
        if _line_env_var_name_only(line):
            return "test_fixture", "test_env_reference", True
        if pattern_label == "api_key_like" and "=" in line:
            value = _assignment_value(line)
            if value is not None and not value_looks_like_real_secret(value):
                return "test_fixture", "test_placeholder_assignment", True
        return "test_fixture", "test_non_production_context", True

    if rel_path.startswith("docs/") or rel_path.startswith("config/") or rel_path in DOCUMENTATION_EXACT_FILES:
        if value_looks_like_real_secret(_assignment_value(line) or ""):
            return "real_secret_risk", "realistic_assignment_in_docs", False
        if _line_env_var_name_only(line):
            return "documentation_reference", "docs_config_reference", True
        return "placeholder_or_example", "docs_config_default", True

    if rel_path.startswith(TOOLING_PATH_PREFIXES) or rel_path.endswith(".env.example"):
        if _line_clears_env_var(line) or _line_env_var_name_only(line):
            return "tooling_pattern_reference", "script_env_reference", True
        return "tooling_pattern_reference", "script_default", True

    if rel_path.startswith(SOURCE_CODE_PREFIXES):
        if _line_env_var_name_only(line):
            return "documentation_reference", "source_env_var_reference", True
        if pattern_label == "gmail_token":
            if value_looks_like_real_secret(_assignment_value(line) or ""):
                return "real_secret_risk", "source_realistic_gmail_assignment", False
            return "documentation_reference", "source_gmail_reference", True
        if pattern_label == "api_key_like" and re.search(
            r"(?:\b(?:token|password|secret)\s*:\s*(?:str|bytes))|api_key_required",
            stripped,
        ):
            return "documentation_reference", "source_identifier_or_status", True
        if pattern_label == "api_key_like" and "=" in line:
            value = _assignment_value(line)
            if value is not None and not value_looks_like_real_secret(value):
                return "documentation_reference", "source_non_secret_assignment", True

    if value_looks_like_real_secret(_assignment_value(line) or ""):
        return "real_secret_risk", "realistic_assignment", False

    return "needs_human_review", "unclassified", False


def evaluate_secret_hit(*, rel_path: str, pattern_label: str, sample_text: str) -> tuple[bool, str, str]:
    pattern = next((p for label, p in SECRET_PATTERNS if label == pattern_label), None)
    if pattern is None:
        return False, "unknown_pattern", "needs_human_review"
    matched: list[tuple[int, str]] = []
    for line_number, line in enumerate(sample_text.splitlines(), start=1):
        if pattern.search(line):
            matched.append((line_number, line))
    if not matched:
        return False, "no_line_match", "needs_human_review"
    for line_number, line in matched:
        category, reason, suppress = classify_hit_category(
            rel_path=rel_path,
            pattern_label=pattern_label,
            line=line,
            line_number=line_number,
        )
        if not suppress:
            return False, reason, category
    category, reason, _suppress = classify_hit_category(
        rel_path=rel_path,
        pattern_label=pattern_label,
        line=matched[0][1],
        line_number=matched[0][0],
    )
    return True, reason, category


def should_suppress_secret_hit(*, rel_path: str, pattern_label: str, sample_text: str) -> bool:
    suppress, _, _ = evaluate_secret_hit(
        rel_path=rel_path,
        pattern_label=pattern_label,
        sample_text=sample_text,
    )
    return suppress


def is_documentation_path(rel_path: str) -> bool:
    if rel_path in DOCUMENTATION_EXACT_FILES:
        return True
    return rel_path.startswith(DOCUMENTATION_PATH_PREFIXES)
