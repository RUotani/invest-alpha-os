"""Paste-file intake readiness (paste_ohlcv_here.tsv → working CSV, no clipboard OS access)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_dropzone import PASTE_FILENAME, default_dropzone_path
from invis_alpha_os.reports.manual_data_normalizer import build_manual_data_normalization
from invis_alpha_os.reports.manual_data_schema_probe import probe_path_ohlcv_schema


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _paste_has_data_rows(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return False
    lines = [line for line in text.splitlines() if line.strip()]
    return len(lines) > 1


@dataclass(frozen=True)
class ManualDataPasteIntakeResult:
    markdown_text: str
    json_payload: dict[str, Any]
    materialized_path: Path | None


def materialize_paste_to_working_csv(
    *,
    dropzone: Path,
    working_dir: Path,
    report_date: str,
) -> ManualDataPasteIntakeResult:
    paste_path = dropzone / PASTE_FILENAME
    working_dir.mkdir(parents=True, exist_ok=True)
    out_path = working_dir / "manual_jp_bars_from_paste.csv"

    if not paste_path.is_file():
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "paste_file_present": False,
            "paste_has_data": False,
            "materialized": False,
            "readiness_status": "paste_file_missing",
            "clipboard_os_read": False,
            "contents_printed": False,
        }
        return ManualDataPasteIntakeResult(
            markdown_text="# Manual Data Paste Intake\n\n- readiness_status: paste_file_missing\n",
            json_payload=payload,
            materialized_path=None,
        )

    has_data = _paste_has_data_rows(paste_path)
    if not has_data:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "paste_file_present": True,
            "paste_has_data": False,
            "materialized": False,
            "readiness_status": "awaiting_paste",
            "clipboard_os_read": False,
            "contents_printed": False,
        }
        return ManualDataPasteIntakeResult(
            markdown_text="# Manual Data Paste Intake\n\n- readiness_status: awaiting_paste\n",
            json_payload=payload,
            materialized_path=None,
        )

    schema_ok, schema_reason = probe_path_ohlcv_schema(paste_path)
    if not schema_ok:
        payload = {
            "report_date": report_date,
            "generated_at": _now_iso(),
            "paste_file_present": True,
            "paste_has_data": True,
            "materialized": False,
            "readiness_status": "header_not_ohlcv",
            "schema_probe_reason": schema_reason,
            "clipboard_os_read": False,
            "contents_printed": False,
        }
        return ManualDataPasteIntakeResult(
            markdown_text=(
                "# Manual Data Paste Intake\n\n"
                f"- readiness_status: header_not_ohlcv\n"
                f"- schema_probe_reason: {schema_reason}\n"
            ),
            json_payload=payload,
            materialized_path=None,
        )

    normalization = build_manual_data_normalization(
        input_path=paste_path,
        report_date=report_date,
        output_path=out_path,
    )
    materialized = normalization.normalized_path
    norm_ok = materialized is not None and materialized.is_file()
    if norm_ok and materialized is not None:
        post_schema, post_reason = probe_path_ohlcv_schema(materialized)
    else:
        post_schema, post_reason = False, "normalization_failed"

    readiness = "ready_for_pipeline" if norm_ok and post_schema else "normalization_failed"
    payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "paste_file_present": True,
        "paste_has_data": True,
        "materialized": norm_ok,
        "materialized_filename": materialized.name if materialized else None,
        "readiness_status": readiness,
        "schema_probe_reason": post_reason,
        "normalization_status": normalization.json_payload.get("overall_status"),
        "clipboard_os_read": False,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Paste Intake Readiness",
        "",
        f"- readiness_status: {readiness}",
        f"- materialized: {str(norm_ok).lower()}",
        "",
    ]
    return ManualDataPasteIntakeResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        materialized_path=materialized if norm_ok and post_schema else None,
    )


def build_manual_data_paste_intake_readiness(
    *,
    report_date: str,
    repo_root: Path,
    dropzone: Path | None = None,
) -> ManualDataPasteIntakeResult:
    dz = dropzone or default_dropzone_path()
    work = repo_root / "outputs" / "manual_data" / "working" / report_date
    return materialize_paste_to_working_csv(dropzone=dz, working_dir=work, report_date=report_date)
