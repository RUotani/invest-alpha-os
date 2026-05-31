"""Source-only Long-Run operator preflight and sleep-guard pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SLEEP_GUARD_COMMAND = "caffeinate -dimsu -t 43200"


def sleep_prevention_markdown_block() -> str:
    return "\n".join(
        [
            "## Operator Preflight - macOS Sleep Prevention",
            "",
            "Before starting a Long-Run Max session on a MacBook, run this in a separate Terminal window:",
            "",
            "```bash",
            SLEEP_GUARD_COMMAND,
            "```",
            "",
            "- Keep the MacBook connected to AC power.",
            "- Keep the lid open.",
            "- Keep the `caffeinate` Terminal window running until the Codex/Cursor run is finished.",
            "- Do not rely on display sleep settings alone.",
            "- Do not change macOS system settings from the coding agent.",
        ]
    )


def hard_gate_markdown_block() -> str:
    return "\n".join(
        [
            "## invest-alpha-os Hard Gates",
            "",
            "Do not execute or modify anything that falls under these gates without explicit human approval:",
            "",
            "- provider live access",
            "- live HTTP",
            "- Tiingo API call",
            "- Stooq / Yahoo / Polygon live fetch",
            "- cache write",
            "- actual refresh/import",
            "- manual actual import",
            "- raw OHLCV persistence",
            "- raw API response persistence",
            "- reports-private raw data write",
            "- Git-tracked raw data write",
            "- env/secret display",
            "- dependency / pyproject changes",
            "- `.github/workflows` direct changes",
            "- broker/manual raw data handling",
            "- trading action",
        ]
    )


def build_long_run_operator_preflight_pack(*, report_date: str) -> dict[str, Any]:
    sleep_block = sleep_prevention_markdown_block()
    hard_gate_block = hard_gate_markdown_block()
    return {
        "pack_version": "v71C",
        "report_name": "long_run_operator_preflight_sleep_guard_pack",
        "source_only": True,
        "report_date": report_date,
        "sleep_prevention": {
            "standardized": True,
            "recommended_command": SLEEP_GUARD_COMMAND,
            "separate_terminal_required": True,
            "ac_power_required": True,
            "lid_open_required": True,
            "keep_terminal_running": True,
            "display_sleep_alone_sufficient": False,
            "agent_macos_settings_change_allowed": False,
            "markdown_block": sleep_block,
        },
        "handoff_inclusion_contract": {
            "future_long_run_max_instructions_include_sleep_guard": True,
            "future_cursor_handoffs_include_sleep_guard": True,
            "future_operator_runbooks_include_sleep_guard": True,
            "operator_prompt_stop_required": False,
        },
        "hard_gate_reminder": {
            "included": True,
            "markdown_block": hard_gate_block,
        },
        "readiness_verdict": "operator_preflight_sleep_guard_standardized_source_only",
        "next_task": "scheduled_report_assurance_snapshot_source_only",
        "safety_summary": {
            "macos_system_settings_changed": False,
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "tiingo_api_call_executed": False,
            "stooq_yahoo_polygon_live_fetch_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "raw_ohlcv_persistence_executed": False,
            "raw_api_response_persistence_executed": False,
            "reports_private_raw_data_written": False,
            "git_tracked_raw_data_written": False,
            "env_secret_displayed": False,
            "workflow_files_modified": False,
            "dependency_pyproject_changed": False,
            "trading_action_executed": False,
        },
    }


def format_long_run_operator_preflight_pack_markdown(payload: dict[str, Any]) -> str:
    sleep = payload["sleep_prevention"]
    lines = [
        "# Long-Run Operator Preflight / Sleep-Guard Pack v71C",
        "",
        "## Verdict",
        f"- readiness_verdict: {payload['readiness_verdict']}",
        f"- sleep_prevention_standardized: {str(sleep['standardized']).lower()}",
        f"- recommended_command: `{sleep['recommended_command']}`",
        "",
        sleep["markdown_block"],
        "",
        "## Handoff Inclusion Contract",
    ]
    for key, value in payload["handoff_inclusion_contract"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", payload["hard_gate_reminder"]["markdown_block"], "", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_long_run_operator_preflight_pack_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_long_run_operator_preflight_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("weekly", weekly)):
        md_path = root / "long_run_operator_preflight_sleep_guard_pack.md"
        json_path = root / "long_run_operator_preflight_sleep_guard_pack.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_long_run_operator_preflight_pack_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_long_run_operator_preflight_sleep_guard_pack_md"] = md_path
        paths[f"{label}_long_run_operator_preflight_sleep_guard_pack_json"] = json_path
    return paths
