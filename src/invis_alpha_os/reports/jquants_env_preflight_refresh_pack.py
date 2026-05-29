"""v29: env discovery + gated refresh preflight + refresh approval package."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.jquants_env_file_discovery import (
    build_jquants_env_file_discovery,
    merge_env_for_preflight,
)
from invis_alpha_os.reports.jquants_gated_refresh_approval_package import (
    build_jquants_gated_refresh_approval_package,
)
from invis_alpha_os.reports.jquants_gated_refresh_preflight import build_jquants_gated_refresh_preflight
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV


@dataclass(frozen=True)
class JQuantsEnvPreflightRefreshPackResult:
    env_discovery: Any
    preflight: Any
    approval_package: Any
    summary: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_jquants_env_preflight_refresh_pack(
    *,
    report_date: str,
    repo_root: Path,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    env_file: Path | None = None,
) -> JQuantsEnvPreflightRefreshPackResult:
    discovery = build_jquants_env_file_discovery(report_date=report_date, repo_root=repo_root)
    selected = env_file or discovery.selected_env_file
    env_map = merge_env_for_preflight(env_file=selected)
    preflight = build_jquants_gated_refresh_preflight(
        report_date=report_date,
        targets_csv=targets_csv,
        env=env_map,
    )
    approval = build_jquants_gated_refresh_approval_package(
        report_date=report_date,
        targets_csv=targets_csv,
        env_discovery=discovery.json_payload,
        preflight=preflight.json_payload,
    )
    summary = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v29",
        "selected_env_file_redacted": discovery.json_payload.get("selected_env_file_redacted"),
        "required_keys_present": discovery.json_payload.get("required_keys_present"),
        "credentials_available": preflight.json_payload.get("credentials_available"),
        "refresh_recommended": preflight.json_payload.get("refresh_recommended"),
        "approval_package_status": approval.json_payload.get("package_status"),
        "max_gap_days": preflight.json_payload.get("max_gap_days"),
        "live_http_executed": False,
        "cache_write_executed": False,
    }
    return JQuantsEnvPreflightRefreshPackResult(
        env_discovery=discovery,
        preflight=preflight,
        approval_package=approval,
        summary=summary,
    )


def write_jquants_env_preflight_refresh_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: JQuantsEnvPreflightRefreshPackResult,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    yyyy = report_date[:4]
    archive = out_dir / "archive" / yyyy / report_date
    latest.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    def _pair(basename: str, md: str, payload: dict[str, Any]) -> None:
        for root, label in ((latest, "latest"), (archive, "archive")):
            md_path = root / f"{basename}.md"
            json_path = root / f"{basename}.json"
            md_path.write_text(md, encoding="utf-8")
            json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{basename}_md"] = md_path
            paths[f"{label}_{basename}_json"] = json_path

    _pair("jquants_env_file_discovery", result.env_discovery.markdown_text, result.env_discovery.json_payload)
    _pair("jquants_gated_refresh_preflight", result.preflight.markdown_text, result.preflight.json_payload)
    _pair(
        "jquants_gated_refresh_approval_package",
        result.approval_package.markdown_text,
        result.approval_package.json_payload,
    )
    summary_path = latest / "jquants_env_preflight_refresh_pack_summary.json"
    summary_path.write_text(json.dumps(result.summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["latest_jquants_env_preflight_refresh_pack_summary_json"] = summary_path
    return paths


def sync_jquants_env_preflight_refresh_pack_to_reports_repo(
    *,
    reports_repo_path: Path,
    report_date: str,
    result: JQuantsEnvPreflightRefreshPackResult,
) -> dict[str, Path]:
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    items = [
        ("jquants_env_file_discovery.md", result.env_discovery.markdown_text),
        ("jquants_env_file_discovery.json", json.dumps(result.env_discovery.json_payload, ensure_ascii=False, indent=2)),
        ("jquants_gated_refresh_preflight.md", result.preflight.markdown_text),
        ("jquants_gated_refresh_preflight.json", json.dumps(result.preflight.json_payload, ensure_ascii=False, indent=2)),
        ("jquants_gated_refresh_approval_package.md", result.approval_package.markdown_text),
        (
            "jquants_gated_refresh_approval_package.json",
            json.dumps(result.approval_package.json_payload, ensure_ascii=False, indent=2),
        ),
        (
            "jquants_env_preflight_refresh_pack_summary.json",
            json.dumps(result.summary, ensure_ascii=False, indent=2),
        ),
    ]
    for basename, content in items:
        for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
            path = root / basename
            path.write_text(content, encoding="utf-8")
            paths[f"{label}_{basename}"] = path
    return paths
