"""Local manual JP bars dropzone helpers (paths outside git, no raw content in reports)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_export_assistant import build_manual_jp_bars_template_csv

DEFAULT_DROPZONE_DIRNAME = "invest-alpha-os-manual-data-dropzone"
README_FILENAME = "README_manual_jp_bars.md"
PASTE_README_FILENAME = "README_paste_to_manual_jp_bars.md"
PASTE_FILENAME = "paste_ohlcv_here.tsv"
TARGET_MANUAL_FILENAME = "manual_jp_bars.csv"
TEMPLATE_FILENAME = "manual_jp_bars_template.csv"

DROPZONE_EXCLUDED_FILENAMES: frozenset[str] = frozenset(
    {
        TEMPLATE_FILENAME,
        PASTE_FILENAME,
        "manual_jp_bars_from_paste.csv",
    }
)

DROPZONE_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "manual_data_intermediate",
    "manual_jp_bars_from_paste",
)


def is_excluded_manual_filename(name: str) -> bool:
    lowered = name.lower()
    if lowered in {n.lower() for n in DROPZONE_EXCLUDED_FILENAMES}:
        return True
    return any(lowered.startswith(prefix) for prefix in DROPZONE_EXCLUDED_PREFIXES)


def default_dropzone_path() -> Path:
    return Path.home() / "Downloads" / DEFAULT_DROPZONE_DIRNAME


def manual_data_search_roots() -> list[Path]:
    home = Path.home()
    return [
        default_dropzone_path(),
        home / "Desktop" / "chatgpt_invest_upload_latest",
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
    ]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_dropzone_readme_text() -> str:
    return "\n".join(
        [
            "# Manual JP Bars Dropzone",
            "",
            "## One action",
            "",
            "Export OHLCV-only from your broker and save as:",
            "",
            "```text",
            f"{TARGET_MANUAL_FILENAME}",
            "```",
            "",
            f"in this folder: `~/{DEFAULT_DROPZONE_DIRNAME}`",
            "",
            "## Or paste from spreadsheet",
            "",
            f"Edit `{PASTE_FILENAME}` (tab-separated), then run:",
            "",
            "```bash",
            ".venv/bin/python -m invis_alpha_os.cli.main "
            "weekly-candidate-brief-manual-data-acquisition-ux-pack",
            "```",
            "",
            "## Required columns",
            "",
            "ticker,date,open,high,low,close,volume",
            "",
            "## Prohibited",
            "",
            "account, name, position, pnl, broker_account, 口座, 氏名, 評価損益, etc.",
            "",
        ]
    )


def build_paste_readme_text() -> str:
    return "\n".join(
        [
            "# Paste OHLCV table here",
            "",
            "1. Copy OHLCV rows from broker or spreadsheet (header row required).",
            f"2. Paste into `{PASTE_FILENAME}` (tab-separated).",
            "3. Run `weekly-candidate-brief-manual-data-acquisition-ux-pack`.",
            "",
            "Do not include account/name/position columns.",
            "",
            "Required header (any alias OK): ticker, date, open, high, low, close, volume",
            "",
        ]
    )


def build_paste_template_tsv() -> str:
    return "ticker\tdate\topen\thigh\tlow\tclose\tvolume\n5802\t\t\t\t\t\t\n"


def ensure_dropzone_assets(*, dropzone: Path | None = None) -> dict[str, Path]:
    root = dropzone or default_dropzone_path()
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    readme = root / README_FILENAME
    readme.write_text(build_dropzone_readme_text(), encoding="utf-8")
    paths["readme"] = readme
    paste_readme = root / PASTE_README_FILENAME
    paste_readme.write_text(build_paste_readme_text(), encoding="utf-8")
    paths["paste_readme"] = paste_readme
    template = root / TEMPLATE_FILENAME
    template.write_text(build_manual_jp_bars_template_csv(), encoding="utf-8")
    paths["template"] = template
    paste_file = root / PASTE_FILENAME
    if not paste_file.exists():
        paste_file.write_text(build_paste_template_tsv(), encoding="utf-8")
    paths["paste_file"] = paste_file
    return paths


@dataclass(frozen=True)
class ManualDataDropzoneStatusResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_manual_data_dropzone_status(
    *,
    report_date: str,
    dropzone: Path | None = None,
) -> ManualDataDropzoneStatusResult:
    root = dropzone or default_dropzone_path()
    assets = ensure_dropzone_assets(dropzone=root)
    manual_present = (root / TARGET_MANUAL_FILENAME).is_file()
    paste_present = (root / PASTE_FILENAME).is_file()
    paste_size = 0
    if paste_present:
        try:
            paste_size = int((root / PASTE_FILENAME).stat().st_size)
        except OSError:
            paste_size = 0
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "dropzone_exists": root.is_dir(),
        "dropzone_path_redacted": True,
        "dropzone_directory_label": f"Downloads/{DEFAULT_DROPZONE_DIRNAME}",
        "manual_jp_bars_present": manual_present,
        "paste_file_present": paste_present,
        "paste_file_size_bytes": paste_size,
        "template_present": assets["template"].is_file(),
        "readme_present": assets["readme"].is_file(),
        "target_filename": TARGET_MANUAL_FILENAME,
        "next_single_action": (
            "Export OHLCV-only CSV from broker and save as manual_jp_bars.csv in the dropzone"
            if not manual_present
            else "Run weekly-candidate-brief-manual-data-acquisition-ux-pack for schema + dry-run"
        ),
        "auto_copy_enabled": False,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Dropzone Status",
        "",
        f"- dropzone_exists: {str(payload['dropzone_exists']).lower()}",
        f"- manual_jp_bars_present: {str(manual_present).lower()}",
        f"- paste_file_present: {str(paste_present).lower()}",
        f"- next_single_action: {payload['next_single_action']}",
        "",
    ]
    return ManualDataDropzoneStatusResult(markdown_text="\n".join(lines), json_payload=payload)
