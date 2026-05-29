"""Redacted provider HTTP error diagnostics for J-Quants cache refresh."""

from __future__ import annotations

from typing import Any

REQUEST_PHASE_DAILY_QUOTES_FETCH = "daily_quotes_fetch"
ENDPOINT_CATEGORY_DAILY_BARS = "daily_bars"


def _coerce_http_status(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def classify_provider_error_class(*, raw_status: str, http_status: int | None, reason: str) -> str:
    reason_lower = reason.strip().lower()
    if raw_status in {"non_json_response"}:
        return "json_parse_error"
    if raw_status in {"invalid_response", "sanitized_empty"}:
        return "schema_error"
    if raw_status in {"error"} and "timeout" in reason_lower:
        return "timeout"
    if raw_status in {"error"}:
        return "network_error"
    if http_status == 400:
        return "http_400_bad_request"
    if http_status == 401:
        return "http_401_unauthorized"
    if http_status == 403:
        return "http_403_forbidden"
    if http_status == 404:
        return "http_404_not_found"
    if http_status == 429:
        return "http_429_rate_limited"
    if http_status is not None and 500 <= http_status <= 599:
        return "http_5xx_provider"
    if raw_status == "http_error":
        return "unknown_http_error"
    return "unknown_http_error"


def provider_error_retry_safe(provider_error_class: str) -> bool:
    return provider_error_class in {
        "http_429_rate_limited",
        "http_5xx_provider",
        "network_error",
        "timeout",
        "unknown_http_error",
    }


def provider_error_next_action(provider_error_class: str) -> str:
    mapping = {
        "http_400_bad_request": "Review request parameters and date range",
        "http_401_unauthorized": "Check J-Quants API key/auth or subscription",
        "http_403_forbidden": "Check J-Quants subscription or endpoint permissions",
        "http_404_not_found": "Check J-Quants base URL/path configuration",
        "http_429_rate_limited": "Wait and retry once after rate limit window",
        "http_5xx_provider": "Retry once after provider outage clears",
        "network_error": "Check network connectivity and retry once",
        "timeout": "Retry once after network timeout clears",
        "json_parse_error": "Inspect provider response format or endpoint contract",
        "schema_error": "Inspect provider response schema or endpoint contract",
        "unknown_http_error": "Inspect provider error and retry once after fix",
    }
    return mapping.get(provider_error_class, "Inspect provider error and retry once after fix")


def build_redacted_provider_diagnostics(raw: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(raw.get("status", ""))
    http_status = _coerce_http_status(raw.get("http_status"))
    reason = str(raw.get("reason", raw.get("hint", raw_status)))
    provider_error_class = classify_provider_error_class(
        raw_status=raw_status,
        http_status=http_status,
        reason=reason,
    )
    body_available = bool(raw.get("error_body_preview"))
    return {
        "provider_error_class": provider_error_class,
        "http_status": http_status,
        "request_phase": str(raw.get("request_phase", REQUEST_PHASE_DAILY_QUOTES_FETCH)),
        "endpoint_category": str(raw.get("endpoint_category", ENDPOINT_CATEGORY_DAILY_BARS)),
        "retry_safe": provider_error_retry_safe(provider_error_class),
        "next_required_action": provider_error_next_action(provider_error_class),
        "response_body_redacted": True,
        "body_available": body_available,
        "body_redacted": body_available,
        "secrets_printed": False,
    }
