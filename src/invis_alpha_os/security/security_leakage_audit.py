"""Redacted security leakage audit for source and reports repositories."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.secret_pattern_suppression import should_suppress_secret_hit

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key_like", re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*\S+", re.MULTILINE)),
    ("jquants_key", re.compile(r"(?i)JQUANTS_API_KEY\s*=", re.MULTILINE)),
    ("alpha_vantage_key", re.compile(r"(?i)ALPHA_VANTAGE_API_KEY\s*=", re.MULTILINE)),
    ("gmail_token", re.compile(r"(?i)(GMAIL_|client_secret|refresh_token)", re.MULTILINE)),
)

BROKER_FILE_SUFFIXES: frozenset[str] = frozenset({".csv", ".tsv", ".xlsx", ".txt"})
SENSITIVE_FILENAMES: frozenset[str] = frozenset(
    {".env", ".env.local", "credentials.json", "token.json", "gmail_token.json"}
)


@dataclass(frozen=True)
class SecurityLeakageAuditResult:
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


def _scan_tracked_paths(repo_root: Path, rel_paths: list[str]) -> dict[str, Any]:
    tracked_env: list[str] = []
    broker_files: list[str] = []
    generated_artifacts: list[str] = []
    secret_hits: list[dict[str, Any]] = []
    suppressed_hits: list[dict[str, Any]] = []

    for rel in rel_paths:
        name = Path(rel).name
        suffix = Path(rel).suffix.lower()
        if name in SENSITIVE_FILENAMES or name.endswith(".env"):
            tracked_env.append(rel)
        if suffix in BROKER_FILE_SUFFIXES and "fixtures" not in rel and "tests/" not in rel:
            if "manual" in name.lower() or "broker" in name.lower() or "jp_bars" in name.lower():
                broker_files.append(rel)
        if rel.endswith(".gitkeep"):
            pass
        elif rel.startswith("reports/") and rel.endswith((".json", ".md", ".csv", ".eml", ".html")):
            generated_artifacts.append(rel)
        elif rel.startswith("outputs/") and not rel.endswith(".gitkeep"):
            generated_artifacts.append(rel)

        abs_path = repo_root / rel
        if abs_path.is_file() and abs_path.stat().st_size < 500_000:
            try:
                sample = abs_path.read_text(encoding="utf-8", errors="ignore")[:8000]
            except OSError:
                continue
            for label, pattern in SECRET_PATTERNS:
                if not pattern.search(sample):
                    continue
                if should_suppress_secret_hit(rel_path=rel, pattern_label=label, sample_text=sample):
                    suppressed_hits.append(
                        {"pattern": label, "path": rel, "redacted": True, "suppressed": True}
                    )
                    continue
                secret_hits.append({"pattern": label, "path": rel, "redacted": True})

    return {
        "tracked_env_files": tracked_env,
        "tracked_broker_files": broker_files,
        "tracked_generated_artifacts": generated_artifacts[:50],
        "suspected_secret_hits": secret_hits,
        "suppressed_false_positives": suppressed_hits[:50],
        "suppressed_false_positive_count": len(suppressed_hits),
    }


def _scan_reports_tree(reports_root: Path) -> dict[str, Any]:
    if not reports_root.is_dir():
        return {"suspected_secret_hits": [], "broker_files": [], "missing": True}
    broker_files: list[str] = []
    secret_hits: list[dict[str, Any]] = []
    suppressed_hits: list[dict[str, Any]] = []
    for path in reports_root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(reports_root))
        suffix = path.suffix.lower()
        if suffix in BROKER_FILE_SUFFIXES and "template" not in rel.lower():
            if "manual_jp_bars" in path.name and "template" not in path.name:
                broker_files.append(rel)
        if path.stat().st_size > 500_000:
            continue
        try:
            sample = path.read_text(encoding="utf-8", errors="ignore")[:8000]
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS:
            if not pattern.search(sample):
                continue
            if should_suppress_secret_hit(rel_path=rel, pattern_label=label, sample_text=sample):
                suppressed_hits.append({"pattern": label, "path": rel, "redacted": True, "suppressed": True})
                continue
            secret_hits.append({"pattern": label, "path": rel, "redacted": True})
    return {
        "suspected_secret_hits": secret_hits,
        "suppressed_false_positives": suppressed_hits[:50],
        "suppressed_false_positive_count": len(suppressed_hits),
        "broker_files": broker_files,
    }


def build_security_leakage_audit(
    *,
    source_repo_path: Path,
    reports_repo_path: Path | None = None,
) -> SecurityLeakageAuditResult:
    rel_paths = _git_tracked_files(source_repo_path)
    source_scan = _scan_tracked_paths(source_repo_path, rel_paths)
    reports_scan: dict[str, Any] = {"skipped": True}
    if reports_repo_path is not None:
        reports_scan = _scan_reports_tree(reports_repo_path)

    high_count = len(source_scan["suspected_secret_hits"]) + len(reports_scan.get("suspected_secret_hits", []))
    high_count += len(source_scan["tracked_env_files"]) + len(source_scan.get("broker_files", []))
    overall = "pass" if high_count == 0 else "review_required"

    payload: dict[str, Any] = {
        "overall_status": overall,
        "generated_at": _now_iso(),
        "secrets_printed": False,
        "source_repo": source_scan,
        "reports_repo": reports_scan,
    }
    lines = [
        "# Security Leakage Audit",
        "",
        f"- overall_status: {overall}",
        f"- secrets_printed: false",
        f"- source_tracked_env_count: {len(source_scan['tracked_env_files'])}",
        f"- source_secret_hit_count: {len(source_scan['suspected_secret_hits'])}",
        f"- suppressed_false_positive_count: {source_scan.get('suppressed_false_positive_count', 0)}",
        "",
    ]
    return SecurityLeakageAuditResult(markdown_text="\n".join(lines), json_payload=payload)
