"""Target-specific manual data export package when no local file is available."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS
from invis_alpha_os.reports.manual_csv_template import DEFAULT_TARGETS, build_manual_csv_template
from invis_alpha_os.reports.manual_data_discovery import SUPPORTED_EXTENSIONS, _location_label, _search_roots


@dataclass(frozen=True)
class ManualDataExportPackageResult:
    markdown_text: str
    json_payload: dict[str, Any]
    template_csv_text: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _per_target_cache_state(targets: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker in targets:
        loaded = load_jquants_daily_bars_cache(ticker)
        latest: str | None = None
        if loaded:
            bars, _meta = loaded
            if bars:
                latest = str(bars[-1]["date"])
        rows.append(
            {
                "ticker": ticker,
                "cache_latest_date": latest,
                "desired_rows_after": latest,
                "suggested_filename": f"manual_jp_bars_{ticker}.csv",
            }
        )
    return rows


def build_manual_data_export_package(
    *,
    targets_csv: str = ",".join(DEFAULT_TARGETS),
    report_date: str,
) -> ManualDataExportPackageResult:
    targets = [part.strip() for part in targets_csv.split(",") if part.strip()]
    per_target = _per_target_cache_state(targets)
    template = build_manual_csv_template(targets_csv=targets_csv, report_date=report_date)
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "required_targets": targets,
        "per_target": per_target,
        "required_columns": list(CANONICAL_COLUMNS),
        "prohibited_columns": [
            "account",
            "account_number",
            "口座番号",
            "氏名",
            "取引",
            "約定",
            "保有数量",
            "評価額",
            "損益",
        ],
        "prohibited_column_hints": ["account", "口座", "取引", "約定", "評価額"],
        "contents_printed": False,
        "supported_formats": list(SUPPORTED_EXTENSIONS),
        "allowed_local_path_labels": [_location_label(root) for root in _search_roots() if root.is_dir()],
        "preferred_filenames": ["manual_jp_bars.csv", "manual_jp_bars.tsv", "manual_jp_bars.xlsx"],
        "exact_next_commands": [
            "weekly-candidate-brief-manual-data-discover",
            "weekly-candidate-brief-manual-data-import-flow --input-path <untracked-path>",
        ],
        "privacy_warning": "Do not commit broker files or include personal/account data.",
        "cache_write_executed": False,
        "actual_import_executed": False,
    }
    lines = [
        "# Manual Data Export Package",
        "",
        "## Required targets",
        "",
    ]
    for row in per_target:
        lines.append(
            f"- {row['ticker']}: cache_latest={row['cache_latest_date']} "
            f"need_rows_after={row['desired_rows_after']}"
        )
    lines.extend(
        [
            "",
            "## Supported formats",
            "",
            f"- {', '.join(SUPPORTED_EXTENSIONS)}",
            "",
            "## Prohibited columns",
            "",
            f"- {', '.join(payload['prohibited_columns'])}",
            "",
            "## Next commands",
            "",
            "```bash",
            "weekly-candidate-brief-manual-data-discover",
            "weekly-candidate-brief-manual-data-import-flow --input-path <untracked-path> --broker-format auto",
            "```",
            "",
        ]
    )
    return ManualDataExportPackageResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        template_csv_text=template.csv_text,
    )
