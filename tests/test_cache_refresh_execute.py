from __future__ import annotations

from invis_alpha_os.reports.cache_refresh_execute import (
    JP_ALLOWED_TARGETS,
    build_cache_refresh_execute,
    build_cache_refresh_execute_dry_run,
    validate_jp_only_gates,
)


def _plan_payload() -> dict:
    return {
        "targets": [
            {
                "ticker": "5802",
                "market": "JP",
                "provider": "jquants",
                "priority": "high",
                "plan_status": "planned_dry_run_only",
            },
            {
                "ticker": "QQQ",
                "market": "US",
                "provider": "us_daily_bars",
                "priority": "medium",
                "plan_status": "planned_dry_run_only",
            },
        ]
    }


def _full_gates_env() -> dict[str, str]:
    return {
        "ALLOW_LIVE_HTTP": "1",
        "CONFIRM_LIVE_HTTP": "YES",
        "ALLOW_CACHE_WRITE": "1",
        "CONFIRM_CACHE_WRITE": "YES",
        "CONFIRM_CACHE_REFRESH": "YES",
        "CONFIRM_TARGETS": "5802,6645,5801",
        "CONFIRM_PROVIDER": "jquants",
        "CONFIRM_SCOPE": "JP_ONLY",
        "JQUANTS_ALLOW_LIVE_HTTP": "true",
    }


def test_execute_dry_run_success_without_live_or_cache_write() -> None:
    result = build_cache_refresh_execute(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=False,
        env={},
    )
    assert result.json_payload["dry_run_only"] is True
    assert result.json_payload["live_http_executed"] is False
    assert result.json_payload["cache_write_executed"] is False
    assert result.json_payload["actual_refresh_executed"] is False
    assert result.json_payload["status"] == "planned_dry_run_only"
    assert "5802" in result.markdown_text
    assert "QQQ" not in result.json_payload.get("targets", [])


def test_execute_refresh_rejected_without_gates() -> None:
    result = build_cache_refresh_execute(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=True,
        env={},
    )
    assert result.json_payload["status"] == "refused_missing_gates"
    assert result.json_payload["actual_refresh_executed"] is False


def test_refused_target_mismatch() -> None:
    status, detail = validate_jp_only_gates(
        env=_full_gates_env(),
        targets=["5802", "6645"],
        provider="jquants",
        scope="JP_ONLY",
        execute_refresh=True,
    )
    assert status == "refused_target_mismatch"
    assert detail


def test_refused_provider_mismatch() -> None:
    status, _ = validate_jp_only_gates(
        env=_full_gates_env(),
        targets=["5802", "6645", "5801"],
        provider="us_daily_bars",
        scope="JP_ONLY",
        execute_refresh=True,
    )
    assert status == "refused_provider_mismatch"


def test_execute_refresh_mocked_success() -> None:
    def _mock_refresh(code: str, _from: str, _to: str) -> dict:
        return {
            "ticker": code,
            "status": "success",
            "sanitized_bar_count": 100,
            "cache_write_executed": True,
            "live_http_executed": True,
        }

    result = build_cache_refresh_execute(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=True,
        env=_full_gates_env(),
        refresh_fn=_mock_refresh,
    )
    assert result.is_result is True
    assert result.json_payload["actual_refresh_executed"] is True
    assert result.json_payload["live_http_executed"] is True
    assert result.json_payload["cache_write_executed"] is True
    assert set(result.json_payload["targets"]) == JP_ALLOWED_TARGETS


def test_build_cache_refresh_execute_dry_run_legacy_helper() -> None:
    result = build_cache_refresh_execute_dry_run(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=False,
        env={},
    )
    assert result.json_payload["dry_run_only"] is True
