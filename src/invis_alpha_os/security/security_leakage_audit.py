"""Redacted security leakage audit for source and reports repositories."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.secret_pattern_suppression import (
    SECRET_PATTERNS,
    classify_hit_category,
    collect_pattern_hits,
    evaluate_secret_hit,
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
    suppressed_by_category: dict[str, int] = {}
    retained_by_category: dict[str, int] = {}

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
                suppress, reason, category = evaluate_secret_hit(
                    rel_path=rel,
                    pattern_label=label,
                    sample_text=sample,
                )
                if suppress:
                    suppressed_hits.append(
                        {
                            "pattern": label,
                            "path": rel,
                            "redacted": True,
                            "suppressed": True,
                            "category": category,
                            "reason": reason,
                        }
                    )
                    suppressed_by_category[category] = suppressed_by_category.get(category, 0) + 1
                    continue
                secret_hits.append({"pattern": label, "path": rel, "redacted": True})
                first_hit = next(
                    (h for h in collect_pattern_hits(rel_path=rel, sample_text=sample) if h.pattern_label == label),
                    None,
                )
                if first_hit is not None:
                    cat, _, _ = classify_hit_category(
                        rel_path=rel,
                        pattern_label=label,
                        line=first_hit.line_text,
                        line_number=first_hit.line_number,
                    )
                    retained_by_category[cat] = retained_by_category.get(cat, 0) + 1

    return {
        "tracked_env_files": tracked_env,
        "tracked_broker_files": broker_files,
        "tracked_generated_artifacts": generated_artifacts[:50],
        "suspected_secret_hits": secret_hits,
        "suppressed_false_positives": suppressed_hits[:50],
        "suppressed_false_positive_count": len(suppressed_hits),
        "suppressed_by_category": suppressed_by_category,
        "retained_by_category": retained_by_category,
    }


def _scan_reports_tree(reports_root: Path) -> dict[str, Any]:
    if not reports_root.is_dir():
        return {"suspected_secret_hits": [], "broker_files": [], "missing": True}
    broker_files: list[str] = []
    secret_hits: list[dict[str, Any]] = []
    suppressed_hits: list[dict[str, Any]] = []
    suppressed_by_category: dict[str, int] = {}
    for path in reports_root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(reports_root)).replace("\\", "/")
        if rel.startswith(".git/") or "/.git/" in f"/{rel}/":
            continue
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
            suppress, reason, category = evaluate_secret_hit(
                rel_path=rel,
                pattern_label=label,
                sample_text=sample,
            )
            if suppress:
                suppressed_hits.append(
                    {
                        "pattern": label,
                        "path": rel,
                        "redacted": True,
                        "suppressed": True,
                        "category": category,
                        "reason": reason,
                    }
                )
                suppressed_by_category[category] = suppressed_by_category.get(category, 0) + 1
                continue
            secret_hits.append({"pattern": label, "path": rel, "redacted": True})
    return {
        "suspected_secret_hits": secret_hits,
        "suppressed_false_positives": suppressed_hits[:50],
        "suppressed_false_positive_count": len(suppressed_hits),
        "suppressed_by_category": suppressed_by_category,
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

    retained_count = len(source_scan["suspected_secret_hits"]) + len(
        reports_scan.get("suspected_secret_hits", [])
    )
    overall = "pass" if retained_count == 0 else "review_required"

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
