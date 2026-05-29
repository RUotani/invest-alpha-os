"""Resolve weekly report directory paths for CLI commands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from invis_alpha_os.config.paths import ROOT_DIR


@dataclass(frozen=True)
class ReportDirResolution:
    path: Path
    resolution_source: str
    used_fallback: bool
    warning: str | None


def resolve_weekly_report_dir(
    *,
    report_date: str,
    report_dir: str | None = None,
    repo_root: Path | None = None,
) -> ReportDirResolution:
    root = repo_root or ROOT_DIR
    if report_dir:
        candidate = Path(report_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        return ReportDirResolution(
            path=candidate,
            resolution_source="cli_option",
            used_fallback=False,
            warning=None,
        )

    env_report_dir = os.environ.get("REPORT_DIR", "").strip()
    if env_report_dir:
        candidate = Path(env_report_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        return ReportDirResolution(
            path=candidate,
            resolution_source="env_report_dir",
            used_fallback=False,
            warning=None,
        )

    fallback = root / "reports" / report_date
    return ReportDirResolution(
        path=fallback,
        resolution_source="root_default",
        used_fallback=True,
        warning=(
            f"report_dir fallback={fallback} "
            "(override with --report-dir or REPORT_DIR env var)"
        ),
    )
