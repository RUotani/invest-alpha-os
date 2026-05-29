from __future__ import annotations

from invis_alpha_os.reports.jquants_gated_refresh_preflight import build_jquants_gated_refresh_preflight


def test_preflight_no_secrets_and_no_http() -> None:
    result = build_jquants_gated_refresh_preflight(
        report_date="2026-05-29",
        targets_csv="5802,285A",
        env={},
    )
    assert result.json_payload["secrets_printed"] is False
    assert result.json_payload["live_http_executed"] is False
    assert result.json_payload["requires_user_approval"] is True
    assert "per_ticker" in result.json_payload
