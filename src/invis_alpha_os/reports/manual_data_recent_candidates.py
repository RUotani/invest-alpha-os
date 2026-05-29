"""Scan recent local CSV/TSV/TXT for OHLCV-shaped headers (metadata only, no raw rows)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_dropzone import is_excluded_manual_filename
from invis_alpha_os.reports.manual_data_schema_probe import probe_path_ohlcv_schema

RECENT_MAX_AGE_DAYS = 14
MAX_FILES_PER_ROOT = 50
SUPPORTED_SUFFIXES: tuple[str, ...] = (".csv", ".tsv", ".txt")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_recent(path: Path, *, max_age_days: int) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return False
    return mtime >= _now_utc() - timedelta(days=max_age_days)


def _should_skip_filename(name: str) -> bool:
    lowered = name.lower()
    if is_excluded_manual_filename(name):
        return True
    if lowered.endswith("_template.csv"):
        return True
    if "template" in lowered and lowered.endswith(".csv"):
        return True
    return False


def scan_recent_ohlcv_candidates(
    roots: list[Path],
    *,
    max_age_days: int = RECENT_MAX_AGE_DAYS,
) -> list[dict[str, Any]]:
    found: list[tuple[float, dict[str, Any]]] = []
    for root in roots:
        if not root.is_dir():
            continue
        scanned = 0
        try:
            paths = sorted(
                (p for p in root.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            continue
        for path in paths:
            if scanned >= MAX_FILES_PER_ROOT:
                break
            if _should_skip_filename(path.name):
                continue
            if not _is_recent(path, max_age_days=max_age_days):
                continue
            scanned += 1
            schema_match, schema_reason = probe_path_ohlcv_schema(path)
            try:
                stat = path.stat()
                modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                size_bytes = int(stat.st_size)
                mtime = stat.st_mtime
            except OSError:
                modified_at = None
                size_bytes = None
                mtime = 0.0
            found.append(
                (
                    mtime,
                    {
                        "filename": path.name,
                        "extension": path.suffix.lower(),
                        "path_redacted": True,
                        "directory_label": _directory_label(path),
                        "file_size_bytes": size_bytes,
                        "modified_at": modified_at,
                        "recent_candidate": True,
                        "schema_ohlcv_candidate": schema_match,
                        "schema_probe_reason": schema_reason,
                        "suggested_dropzone_copy": schema_match,
                        "auto_copy_performed": False,
                        "resolved_path": str(path.resolve()),
                    },
                )
            )
    found.sort(key=lambda item: item[0], reverse=True)
    return [row for _, row in found]


def _directory_label(path: Path) -> str:
    try:
        rel = path.parent.relative_to(Path.home())
        return str(rel).replace("\\", "/") or "home"
    except ValueError:
        return "outside_home"


@dataclass(frozen=True)
class ManualDataRecentCandidatesResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_manual_data_recent_candidates_report(
    *,
    report_date: str,
    roots: list[Path],
) -> ManualDataRecentCandidatesResult:
    rows = scan_recent_ohlcv_candidates(roots)
    public = [{k: v for k, v in row.items() if k != "resolved_path"} for row in rows]
    schema_matches = [r for r in public if r.get("schema_ohlcv_candidate")]
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recent_candidates_found": len(public),
        "schema_ohlcv_matches": len(schema_matches),
        "max_age_days": RECENT_MAX_AGE_DAYS,
        "candidates": public,
        "copy_requires_user_approval": True,
        "auto_copy_performed": False,
        "contents_printed": False,
    }
    lines = [
        "# Manual Data Recent Candidates",
        "",
        f"- recent_candidates_found: {len(public)}",
        f"- schema_ohlcv_matches: {len(schema_matches)}",
        "",
        "| filename | directory | schema_match | modified_at |",
        "| --- | --- | --- | --- |",
    ]
    for row in public[:20]:
        lines.append(
            f"| {row.get('filename', '-')} | {row.get('directory_label', '-')} | "
            f"{str(row.get('schema_ohlcv_candidate', False)).lower()} | {row.get('modified_at') or '-'} |"
        )
    if not public:
        lines.append("| (none) | - | - | - |")
    lines.append("")
    return ManualDataRecentCandidatesResult(markdown_text="\n".join(lines), json_payload=payload)
