"""Classify tracked/untracked generated artifacts in the source repo."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CLASSIFICATIONS = frozenset(
    {
        "keep_source_tracked",
        "move_to_reports_private",
        "untrack_generated",
        "ignore_local_only",
        "needs_human_review",
        "critical_do_not_track",
    }
)

KEEP_REPORTS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^reports/.*/sample_weekly_observation_report_v1\.md$"),
)

UNTRACK_REPORTS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^reports/\d{4}-\d{2}-\d{2}/.*\.(md|json|csv|eml|html|txt)$"),
    re.compile(r"^reports/weekly_candidate_brief"),
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.env(\.|$)"),
    re.compile(r"credentials.*\.json$", re.I),
    re.compile(r"token.*\.json$", re.I),
    re.compile(r"client_secret", re.I),
)

BROKER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"manual_jp_bars\.(csv|tsv|txt|xlsx)$", re.I),
    re.compile(r"broker_jp_bars\.", re.I),
    re.compile(r"moomoo_jp_bars\.", re.I),
    re.compile(r"sbi_jp_bars\.", re.I),
    re.compile(r"rakuten_jp_bars\.", re.I),
)


@dataclass(frozen=True)
class SourceGeneratedTrackingPlanResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_tracked_files(repo_root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _matches_any(path: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(p.search(path) for p in patterns)


def classify_tracked_path(path: str) -> str:
    if _matches_any(path, SECRET_PATTERNS):
        return "critical_do_not_track"
    if _matches_any(path, BROKER_PATTERNS):
        return "ignore_local_only"
    if path.startswith("tests/") or path.startswith("docs/"):
        return "keep_source_tracked"
    if path.endswith(".gitkeep"):
        return "keep_source_tracked"
    if _matches_any(path, KEEP_REPORTS_PATTERNS):
        return "keep_source_tracked"
    if _matches_any(path, UNTRACK_REPORTS_PATTERNS):
        return "untrack_generated"
    if path.startswith("reports/") and path.endswith((".md", ".json", ".csv", ".eml", ".html")):
        return "untrack_generated"
    if path.startswith("outputs/") and not path.endswith(".gitkeep"):
        return "untrack_generated"
    if path.startswith("cache/"):
        return "untrack_generated"
    if "email_preview" in path or path.endswith(".eml"):
        return "untrack_generated"
    if "chatgpt_context" in path and path.endswith((".md", ".json")):
        return "untrack_generated"
    if path.startswith("reports/") or path.startswith("outputs/"):
        return "needs_human_review"
    return "needs_human_review"


def build_source_generated_tracking_plan(*, source_repo_path: Path) -> SourceGeneratedTrackingPlanResult:
    tracked = _git_tracked_files(source_repo_path)
    items: list[dict[str, Any]] = []
    counts: dict[str, int] = {c: 0 for c in CLASSIFICATIONS}

    scan_patterns = (
        r"^(reports|outputs|cache|data)/",
        r"\.eml$",
        r"email_preview",
        r"weekly_candidate",
        r"chatgpt_context",
        r"manual_.*\.(csv|tsv|txt|xlsx)$",
    )
    combined = re.compile("|".join(f"({p})" for p in scan_patterns), re.I)

    for path in tracked:
        if not combined.search(path):
            continue
        classification = classify_tracked_path(path)
        counts[classification] = counts.get(classification, 0) + 1
        items.append({"path": path, "classification": classification, "tracked": True})

    tracked_reports = [p for p in tracked if p.startswith("reports/")]
    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "source_repo": str(source_repo_path),
        "tracked_reports_count": len(tracked_reports),
        "items": items,
        "classification_counts": counts,
        "de_index_recommended": [i["path"] for i in items if i["classification"] == "untrack_generated"],
        "archive_destination": "invest-alpha-os-reports-private",
        "contents_printed": False,
        "local_file_deletion": False,
    }
    lines = [
        "# Source Generated Tracking Plan",
        "",
        f"- tracked_reports_count: {len(tracked_reports)}",
        f"- untrack_generated_count: {counts.get('untrack_generated', 0)}",
        f"- keep_source_tracked_count: {counts.get('keep_source_tracked', 0)}",
        f"- needs_human_review_count: {counts.get('needs_human_review', 0)}",
        f"- archive_destination: {payload['archive_destination']}",
        "",
        "## Classifications",
        "",
    ]
    for key in sorted(CLASSIFICATIONS):
        lines.append(f"- {key}: {counts.get(key, 0)}")
    lines.append("")
    return SourceGeneratedTrackingPlanResult(markdown_text="\n".join(lines), json_payload=payload)
