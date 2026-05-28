from __future__ import annotations

from invis_alpha_os.reports.jquants_preflight import assess_jquants_credentials, build_jquants_preflight


def test_assess_jquants_credentials_missing_env() -> None:
    diag = assess_jquants_credentials({})
    assert diag["jquants_enabled"] is False
    assert diag["api_base_url_present"] is False
    assert diag["api_key_present"] is False
    assert diag["refresh_allowed"] is False
    assert "JQUANTS_ENABLED" in diag["missing_env"]
    assert diag["secrets_printed"] is False
    assert diag["live_http_executed"] is False


def test_assess_jquants_credentials_present_without_printing_values() -> None:
    diag = assess_jquants_credentials(
        {
            "JQUANTS_ENABLED": "true",
            "JQUANTS_API_BASE_URL": "https://example.test/v2",
            "JQUANTS_API_KEY": "secret-value-not-in-output",
        }
    )
    assert diag["refresh_allowed"] is True
    assert diag["missing_env"] == []
    text = str(diag)
    assert "secret-value-not-in-output" not in text


def test_build_jquants_preflight_markdown() -> None:
    result = build_jquants_preflight(report_date="2026-05-27", env={})
    assert "J-Quants Preflight" in result.markdown_text
    assert result.json_payload["refresh_allowed"] is False
