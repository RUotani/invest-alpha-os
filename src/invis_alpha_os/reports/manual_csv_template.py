"""Manual CSV template and export guide for JP daily bars import."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS

DEFAULT_TARGETS: tuple[str, ...] = ("5802", "6645", "5801", "285A", "5803")


@dataclass(frozen=True)
class ManualCsvTemplateResult:
    markdown_text: str
    csv_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets_csv(targets_csv: str) -> list[str]:
    return [part.strip() for part in targets_csv.split(",") if part.strip()]


def build_manual_csv_template(
    *,
    targets_csv: str = ",".join(DEFAULT_TARGETS),
    report_date: str,
) -> ManualCsvTemplateResult:
    targets = _parse_targets_csv(targets_csv)
    header = ",".join(CANONICAL_COLUMNS)
    example_rows = [
        f"{ticker},YYYY-MM-DD,0,0,0,0,0" for ticker in targets[:2]
    ]
    csv_text = "\n".join([header, *example_rows, ""])
    lines = [
        "# Manual CSV Template",
        "",
        "Use this template when exporting JP daily bars from a broker for gated manual_csv import.",
        "",
        "## Required columns",
        "",
        f"- {', '.join(CANONICAL_COLUMNS)}",
        "",
        "## Allowed ticker aliases",
        "",
        "- Plain code: `5802`, `285A`",
        "- Exchange suffix stripped: `5802.T` -> `5802`",
        "",
        "## Date formats",
        "",
        "- `YYYY-MM-DD` (preferred)",
        "- `YYYY/MM/DD`",
        "- `YYYYMMDD`",
        "",
        "## Targets for this template",
        "",
        f"- {', '.join(targets)}",
        "",
        "## Safety",
        "",
        "- Do not commit broker CSV files to the source repo.",
        "- Place the filled CSV outside git-tracked paths.",
        "- Run validate -> import-plan -> import-execute (dry-run) before any gated import.",
        "",
        "## CLI flow",
        "",
        "```bash",
        "weekly-candidate-brief-manual-csv-validate --csv-path /path/to/manual_jp_bars.csv",
        "weekly-candidate-brief-manual-csv-import-plan --csv-path /path/to/manual_jp_bars.csv",
        "weekly-candidate-brief-manual-csv-import-execute --csv-path /path/to/manual_jp_bars.csv",
        "```",
        "",
    ]
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "provider": "manual_csv",
        "targets": targets,
        "columns": list(CANONICAL_COLUMNS),
        "cache_write_executed": False,
        "actual_import_executed": False,
    }
    return ManualCsvTemplateResult(
        markdown_text="\n".join(lines),
        csv_text=csv_text,
        json_payload=payload,
    )
