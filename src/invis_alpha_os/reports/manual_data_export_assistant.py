"""Human-minimal export assistant when manual JP bars file is missing or invalid."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV

PLACEMENT_HINTS: tuple[str, ...] = (
    "~/Downloads/manual_jp_bars.csv",
    "~/Desktop/manual_jp_bars.csv",
    "~/Documents/manual_jp_bars.csv",
)

HUMAN_STEPS: tuple[str, ...] = (
    "Export OHLCV-only daily bars from your broker (no account/name/position columns).",
    "Save as manual_jp_bars.csv on Downloads or Desktop.",
    "Re-run weekly-candidate-brief-manual-data-freshness-pipeline (dry-run only).",
)


@dataclass(frozen=True)
class ManualDataExportAssistantResult:
    markdown_text: str
    json_payload: dict[str, Any]
    template_csv_text: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manual_jp_bars_template_csv(*, targets_csv: str = DEFAULT_TARGET_TICKERS_CSV) -> str:
    tickers = [t.strip() for t in targets_csv.split(",") if t.strip()]
    lines = [",".join(CANONICAL_COLUMNS)]
    for ticker in tickers:
        lines.append(f"{ticker},,,,,,")
    return "\n".join(lines) + "\n"


def build_manual_data_export_assistant(
    *,
    report_date: str,
    targets_csv: str = DEFAULT_TARGET_TICKERS_CSV,
    reason: str = "manual_file_not_ready",
) -> ManualDataExportAssistantResult:
    template = build_manual_jp_bars_template_csv(targets_csv=targets_csv)
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "reason": reason,
        "required_filename": "manual_jp_bars.csv",
        "placement_hints": list(PLACEMENT_HINTS),
        "required_columns": list(CANONICAL_COLUMNS),
        "prohibited_column_tokens": [
            "account",
            "name",
            "position",
            "pnl",
            "broker_account",
            "口座",
            "氏名",
            "評価損益",
        ],
        "target_tickers": [t.strip() for t in targets_csv.split(",") if t.strip()],
        "human_steps": list(HUMAN_STEPS),
        "do_not_commit_broker_raw": True,
        "template_generated": True,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Export Assistant",
        "",
        f"- reason: {reason}",
        "",
        "## 3 steps",
        "",
    ]
    for index, step in enumerate(HUMAN_STEPS, start=1):
        lines.append(f"{index}. {step}")
    lines.extend(
        [
            "",
            "## Placement hints",
            "",
        ]
    )
    for hint in PLACEMENT_HINTS:
        lines.append(f"- {hint}")
    lines.extend(
        [
            "",
            "## Required columns",
            "",
            f"- {', '.join(CANONICAL_COLUMNS)}",
            "",
            "## Prohibited (do not include)",
            "",
            "- account, name, position, pnl, broker_account, 口座, 氏名, 評価損益, etc.",
            "",
        ]
    )
    return ManualDataExportAssistantResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        template_csv_text=template,
    )
