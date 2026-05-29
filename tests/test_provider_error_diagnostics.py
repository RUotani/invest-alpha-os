from __future__ import annotations

from invis_alpha_os.reports.provider_error_diagnostics import (
    build_redacted_provider_diagnostics,
    classify_provider_error_class,
    provider_error_retry_safe,
)


def test_classify_http_401_unauthorized() -> None:
    assert (
        classify_provider_error_class(raw_status="http_error", http_status=401, reason="http_error")
        == "http_401_unauthorized"
    )
    assert provider_error_retry_safe("http_401_unauthorized") is False


def test_classify_http_429_rate_limited() -> None:
    assert (
        classify_provider_error_class(raw_status="http_error", http_status=429, reason="rate limit")
        == "http_429_rate_limited"
    )
    assert provider_error_retry_safe("http_429_rate_limited") is True


def test_build_redacted_provider_diagnostics_masks_body() -> None:
    diag = build_redacted_provider_diagnostics(
        {
            "status": "http_error",
            "http_status": 401,
            "reason": "http_error",
            "error_body_preview": "masked preview only",
            "request_phase": "daily_quotes_fetch",
        }
    )
    assert diag["provider_error_class"] == "http_401_unauthorized"
    assert diag["http_status"] == 401
    assert diag["response_body_redacted"] is True
    assert diag["body_available"] is True
    assert diag["secrets_printed"] is False
    assert "masked preview only" not in str(diag)


def test_classify_network_error_without_http_status() -> None:
    assert classify_provider_error_class(raw_status="error", http_status=None, reason="connection reset") == "network_error"
