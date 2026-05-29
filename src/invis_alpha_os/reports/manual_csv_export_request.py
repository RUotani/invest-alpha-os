"""Export request checklist when no local manual/broker CSV is available."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_csv_discovery import CANDIDATE_FILENAMES, _location_label, _search_roots
from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS
from invis_alpha_os.reports.manual_csv_template import DEFAULT_TARGETS

PREFERRED_FILENAME = "manual_jp_bars.csv"


@dataclass(frozen=True)
class ManualCsvExportRequestResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _desired_date_range(targets: list[str]) -> dict[str, str | None]:
    min_date: str | None = None
    max_needed: str | None = None
    for ticker in targets:
        loaded = load_jquants_daily_bars_cache(ticker)
        if not loaded:
            continue
        bars, _meta = loaded
        if not bars:
            continue
        latest = str(bars[-1]["date"])
        if max_needed is None or latest > max_needed:
            max_needed = latest
        if min_date is None or latest < min_date:
            min_date = latest
    return {
        "cache_latest_min_across_targets": min_date,
        "need_rows_after": max_needed,
        "suggested_export_from": max_needed,
    }


def build_manual_csv_export_request(
    *,
    targets_csv: str = ",".join(DEFAULT_TARGETS),
    report_date: str,
) -> ManualCsvExportRequestResult:
    targets = [part.strip() for part in targets_csv.split(",") if part.strip()]
    date_range = _desired_date_range(targets)
    allowed_paths = [
        _location_label(root) for root in _search_roots() if root.is_dir()
    ]
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "required_targets": targets,
        "desired_date_range": date_range,
        "preferred_filename": PREFERRED_FILENAME,
        "allowed_local_paths": allowed_paths,
        "allowed_filenames": list(CANDIDATE_FILENAMES),
        "required_columns": list(CANONICAL_COLUMNS),
        "prohibited_column_hints": [
            "account",
            "口座",
            "氏名",
            "取引",
            "約定",
            "評価額",
        ],
        "next_command": "weekly-candidate-brief-manual-csv-import-flow --csv-path <untracked-path>",
        "privacy_warning": "Do not commit broker CSV files or include account/personal data.",
        "cache_write_executed": False,
        "actual_import_executed": False,
    }
    lines = [
        "# Manual CSV Export Request",
        "",
        "## Required targets",
        "",
        f"- {', '.join(targets)}",
        "",
        "## Desired date range",
        "",
        f"- need_rows_after: {date_range.get('need_rows_after')}",
        f"- suggested_export_from: {date_range.get('suggested_export_from')}",
        "",
        "## Preferred filename",
        "",
        f"- {PREFERRED_FILENAME}",
        "",
        "## Required columns",
        "",
        f"- {', '.join(CANONICAL_COLUMNS)}",
        "",
        "## Prohibited data",
        "",
        "- Account numbers, names, addresses, trade history, positions, PnL",
        "",
        "## Next command",
        "",
        "```bash",
        "weekly-candidate-brief-manual-csv-discover",
        "weekly-candidate-brief-manual-csv-import-flow --csv-path <untracked-path>",
        "```",
        "",
        "## Privacy",
        "",
        "- Do not commit broker CSV to source or reports-private repos.",
        "",
    ]
    return ManualCsvExportRequestResult(markdown_text="\n".join(lines), json_payload=payload)
