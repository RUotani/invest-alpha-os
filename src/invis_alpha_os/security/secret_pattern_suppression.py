"""Suppress placeholder/example secret pattern false positives in docs/config."""

from __future__ import annotations

import re

DOCUMENTATION_PATH_PREFIXES: tuple[str, ...] = (
    "docs/",
    "config/",
    "tests/",
)

DOCUMENTATION_EXACT_FILES: frozenset[str] = frozenset({".env.example"})

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


def is_documentation_path(rel_path: str) -> bool:
    if rel_path in DOCUMENTATION_EXACT_FILES:
        return True
    return rel_path.startswith(DOCUMENTATION_PATH_PREFIXES)


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


def should_suppress_secret_hit(*, rel_path: str, pattern_label: str, sample_text: str) -> bool:
    if not is_documentation_path(rel_path):
        return False
    if rel_path.endswith(".env") and not rel_path.endswith(".env.example"):
        return False

    for line in sample_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lower = stripped.lower()
        if pattern_label in {"api_key_like", "jquants_key", "alpha_vantage_key"}:
            if "=" not in stripped:
                continue
            value = _assignment_value(stripped)
            if value is None:
                continue
            if value_looks_like_real_secret(value):
                return False
            if value_looks_like_placeholder(value):
                return True
        elif pattern_label == "gmail_token":
            if "=" in stripped:
                value = _assignment_value(stripped)
                if value is not None:
                    if value_looks_like_real_secret(value):
                        return False
                    if value_looks_like_placeholder(value):
                        return True
            prose_markers = (
                "checklist",
                "dryrun",
                "dry-run",
                "documentation",
                "example",
                "placeholder",
                "do not",
                "never commit",
            )
            if any(marker in lower for marker in prose_markers):
                return True
            if "client_secret" in lower and "=" not in stripped:
                return True
            if lower.startswith("gmail_") and "=" not in stripped:
                return True
    return True
