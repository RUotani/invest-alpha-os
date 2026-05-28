from __future__ import annotations

from invis_alpha_os.reports.cache_refresh_execute import (
    JP_ALLOWED_TARGETS,
    build_cache_refresh_execute,
    build_cache_refresh_execute_dry_run,
    normalize_target_status,
    retry_safe,
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
        "JQUANTS_ENABLED": "true",
        "JQUANTS_API_BASE_URL": "https://example.test/v2",
        "JQUANTS_API_KEY": "test-key",
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
    assert result.json_payload["actual_refresh_executed"] is False
    assert result.json_payload["status"] == "planned_dry_run_only"


def test_execute_refresh_rejected_without_gates() -> None:
    result = build_cache_refresh_execute(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=True,
        env={},
    )
    assert result.json_payload["overall_status"] == "gate_refused"
    assert result.json_payload["actual_refresh_executed"] is False
    assert result.json_payload["retry_safe"] is True


def test_execute_refresh_auth_missing_with_gates_only() -> None:
    env = _full_gates_env()
    env.pop("JQUANTS_API_KEY")
    env.pop("JQUANTS_API_BASE_URL")
    env["JQUANTS_ENABLED"] = "false"
    result = build_cache_refresh_execute(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=True,
        env=env,
    )
    assert result.is_result is True
    assert result.json_payload["overall_status"] == "auth_missing"
    assert result.json_payload["cache_write_executed"] is False
    assert result.json_payload["retry_safe"] is True
    assert "J-Quants" in result.json_payload["next_required_action"]


def test_normalize_target_status_maps_disabled_to_auth_missing() -> None:
    row = normalize_target_status({"ticker": "5802", "status": "disabled", "hint": "JQUANTS_ENABLED=false"})
    assert row["status"] == "auth_missing"
    assert row["live_http_executed"] is False


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
    assert result.json_payload["overall_status"] == "success"
    assert result.json_payload["actual_refresh_executed"] is True
    assert set(result.json_payload["targets"]) == JP_ALLOWED_TARGETS
    assert retry_safe("success") is False


def test_build_cache_refresh_execute_dry_run_legacy_helper() -> None:
    result = build_cache_refresh_execute_dry_run(
        report_date="2026-05-27",
        plan_json_payload=_plan_payload(),
        execute_refresh=False,
        env={},
    )
    assert result.json_payload["dry_run_only"] is True
