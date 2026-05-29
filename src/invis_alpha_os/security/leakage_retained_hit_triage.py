"""Triage retained security leakage hits without printing secret values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.security.secret_pattern_suppression import should_suppress_secret_hit
from invis_alpha_os.security.security_leakage_audit import (
    SECRET_PATTERNS,
    _git_tracked_files,
    build_security_leakage_audit,
)


@dataclass(frozen=True)
class PatternHit:
    pattern_label: str
    line_number: int
    line_text: str


@dataclass(frozen=True)
class LeakageRetainedHitTriageResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redacted_excerpt(line: str) -> str:
    text = line.strip()
    if "=" in text:
        key, _, _val = text.partition("=")
        return f"{key.strip()}=[REDACTED]"
    if len(text) > 120:
        return text[:80] + "...[TRUNCATED]"
    return text


def _collect_pattern_hits(
    *,
    rel_path: str,
    sample_text: str,
) -> list[PatternHit]:
    hits: list[PatternHit] = []
    for line_number, line in enumerate(sample_text.splitlines(), start=1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                hits.append(PatternHit(pattern_label=label, line_number=line_number, line_text=line))
    return hits


def _classify_line(*, rel_path: str, pattern_label: str, line: str) -> tuple[str, str, bool]:
    if should_suppress_secret_hit(
        rel_path=rel_path,
        pattern_label=pattern_label,
        sample_text=line,
    ):
        return "documentation_reference", "documentation_suppression", True
    if rel_path.startswith("tests/"):
        return "test_fixture", "test_context", False
    return "needs_human_review", "unclassified", False


def _triage_path_hits(
    *,
    repo_root: Path,
    rel_paths: list[str],
    repo_label: str,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for rel in rel_paths:
        abs_path = repo_root / rel
        if not abs_path.is_file() or abs_path.stat().st_size > 500_000:
            continue
        try:
            sample = abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for hit in _collect_pattern_hits(rel_path=rel, sample_text=sample):
            category, reason, suppress = _classify_line(
                rel_path=rel,
                pattern_label=hit.pattern_label,
                line=hit.line_text,
            )
            items.append(
                {
                    "repo": repo_label,
                    "path": rel,
                    "line_number": hit.line_number,
                    "pattern": hit.pattern_label,
                    "classification": category,
                    "recommended_action": (
                        "suppress_with_rule" if suppress else "keep_for_review"
                    ),
                    "suppression_reason": reason if suppress else None,
                    "redacted_excerpt": _redacted_excerpt(hit.line_text),
                    "retained": not suppress,
                }
            )
    return items


def build_leakage_retained_hit_triage(
    *,
    source_repo_path: Path,
    reports_repo_path: Path | None = None,
) -> LeakageRetainedHitTriageResult:
    audit = build_security_leakage_audit(
        source_repo_path=source_repo_path,
        reports_repo_path=reports_repo_path,
    )
    source_paths = _git_tracked_files(source_repo_path)
    items = _triage_path_hits(repo_root=source_repo_path, rel_paths=source_paths, repo_label="source")

    if reports_repo_path is not None and reports_repo_path.is_dir():
        for path in reports_repo_path.rglob("*"):
            if not path.is_file() or path.stat().st_size > 500_000:
                continue
            rel = str(path.relative_to(reports_repo_path)).replace("\\", "/")
            if rel.startswith(".git/") or "/.git/" in f"/{rel}/":
                continue
            items.extend(
                _triage_path_hits(
                    repo_root=reports_repo_path,
                    rel_paths=[rel],
                    repo_label="reports_private",
                )
            )

    retained = [i for i in items if i["retained"]]
    suppressed = [i for i in items if not i["retained"]]
    by_class: dict[str, int] = {}
    for item in items:
        cls = str(item["classification"])
        by_class[cls] = by_class.get(cls, 0) + 1

    payload: dict[str, Any] = {
        "generated_at": _now_iso(),
        "secrets_printed": False,
        "leakage_audit_status": audit.json_payload.get("overall_status"),
        "total_hit_count": len(items),
        "retained_hit_count": len(retained),
        "suppressed_hit_count": len(suppressed),
        "classification_counts": by_class,
        "retained_hits": retained[:100],
        "suppressed_hits_sample": suppressed[:30],
    }
    lines = [
        "# Leakage Retained Hit Triage",
        "",
        f"- leakage_audit_status: {payload['leakage_audit_status']}",
        f"- retained_hit_count: {len(retained)}",
        f"- suppressed_hit_count: {len(suppressed)}",
        "",
        "## Classification counts",
        "",
    ]
    for key in sorted(by_class):
        lines.append(f"- {key}: {by_class[key]}")
    lines.extend(["", "## Retained hits (redacted)", ""])
    for item in retained[:40]:
        lines.append(
            f"- [{item['repo']}] {item['path']}:{item['line_number']} "
            f"{item['pattern']} -> {item['classification']}"
        )
    lines.append("")
    return LeakageRetainedHitTriageResult(markdown_text="\n".join(lines), json_payload=payload)
