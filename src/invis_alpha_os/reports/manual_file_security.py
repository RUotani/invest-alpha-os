"""Security guards for manual/broker file intake."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROW_COUNT = 100_000
MAX_COLUMN_COUNT = 50
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t=", "\r=")


@dataclass(frozen=True)
class ManualFileSecurityResult:
    status: str
    issues: list[str]
    json_payload: dict[str, Any]


def _reject_path_traversal(path: Path) -> list[str]:
    issues: list[str] = []
    if ".." in path.parts:
        issues.append("path_traversal_detected")
    try:
        if path.is_symlink():
            issues.append("symlink_not_allowed")
    except OSError:
        issues.append("path_stat_failed")
    return issues


def _binary_guard(path: Path) -> list[str]:
    try:
        sample = path.read_bytes()[:4096]
    except OSError as exc:
        return [f"read_failed:{exc.__class__.__name__}"]
    if b"\x00" in sample:
        return ["binary_content_detected"]
    return []


def _formula_injection_in_text(text: str) -> list[str]:
    issues: list[str] = []
    for line_no, line in enumerate(text.splitlines()[:5000], start=1):
        for cell in line.split(","):
            stripped = cell.strip()
            if stripped.startswith(FORMULA_PREFIXES):
                issues.append(f"formula_injection_row_{line_no}")
                break
        if len(issues) >= 5:
            break
    return issues


def scan_manual_file_security(path: Path) -> ManualFileSecurityResult:
    issues: list[str] = []
    issues.extend(_reject_path_traversal(path))
    if not path.is_file():
        issues.append("file_not_found")
        return ManualFileSecurityResult(status="rejected", issues=issues, json_payload={"issues": issues})

    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        issues.append("file_too_large")

    issues.extend(_binary_guard(path))

    try:
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
    except OSError as exc:
        issues.append(f"read_failed:{exc.__class__.__name__}")
        text = ""

    if text:
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) > MAX_ROW_COUNT:
            issues.append("row_count_exceeded")
        if lines:
            header_cols = lines[0].split(",")
            if len(header_cols) > MAX_COLUMN_COUNT:
                issues.append("column_count_exceeded")
        issues.extend(_formula_injection_in_text(text))

    status = "passed" if not issues else "rejected"
    return ManualFileSecurityResult(
        status=status,
        issues=issues,
        json_payload={
            "status": status,
            "issues": issues,
            "file_size_bytes": size,
            "contents_printed": False,
        },
    )
