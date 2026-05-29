"""Single next action for JP manual OHLCV freshness (no live HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.manual_data_dropzone import default_dropzone_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ManualDataNextSourceActionResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_manual_data_next_source_action(
    *,
    report_date: str,
    jquants_preflight: dict[str, Any],
    alternative_strategy: dict[str, Any],
    approval_package: dict[str, Any],
) -> ManualDataNextSourceActionResult:
    next_best = alternative_strategy.get("next_best_ohlcv_source", "unknown")
    actual_import_rec = bool(approval_package.get("actual_import_recommended"))
    refresh_rec = bool(jquants_preflight.get("refresh_recommended"))

    if actual_import_rec:
        single = "Approve actual import only if rows_newer_than_cache > 0 (currently not recommended)"
    elif refresh_rec:
        single = "Approve J-Quants gated refresh (phrase: J-Quants gated refreshを実行してよい), then re-export CSV"
    elif next_best == "yahoo_finance_jp_manual_export":
        single = "Export OHLCV-only CSV from Yahoo Finance Japan into dropzone as manual_jp_bars.csv"
    else:
        single = "Obtain fresher OHLCV CSV (not from existing cache) and place in dropzone"

    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "next_single_action": single,
        "next_best_ohlcv_source": next_best,
        "actual_import_recommended": actual_import_rec,
        "jquants_refresh_recommended": refresh_rec,
        "dropzone_directory_label": f"Downloads/{default_dropzone_path().name}",
        "approval_phrases": {
            "jquants_refresh": "J-Quants gated refreshを実行してよい",
            "public_fetch": "public OHLCV source live fetchを実行してよい",
            "actual_import": approval_package.get("required_approval_phrase"),
        },
        "live_http_executed": False,
        "cache_write_executed": False,
    }
    lines = [
        "# Manual Data Next Source Action",
        "",
        f"- next_single_action: {single}",
        f"- next_best_ohlcv_source: {next_best}",
        f"- actual_import_recommended: {str(actual_import_rec).lower()}",
        "",
    ]
    return ManualDataNextSourceActionResult(markdown_text="\n".join(lines), json_payload=payload)
