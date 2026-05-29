"""Boolean environment flag parsing helpers."""

from __future__ import annotations

PROVIDER_ALLOW_TRUE_VALUES: frozenset[str] = frozenset({"true", "1", "yes", "y", "on"})
PROVIDER_ALLOW_FALSE_VALUES: frozenset[str] = frozenset({"false", "0", "no", "n", "off", ""})
STRICT_CONFIRM_TRUE_VALUES: frozenset[str] = frozenset({"yes"})


def normalize_env_token(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def provider_allow_flag_truthy(value: str | None) -> bool:
    return normalize_env_token(value) in PROVIDER_ALLOW_TRUE_VALUES


def strict_confirm_flag_truthy(value: str | None, *, expected: str = "YES") -> bool:
    if value is None:
        return False
    return value.strip() == expected


def general_env_truthy(value: str | None) -> bool:
    return normalize_env_token(value) in {"1", "true", "yes"}
