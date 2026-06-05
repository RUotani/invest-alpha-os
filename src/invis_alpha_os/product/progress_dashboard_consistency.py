"""Consistency checker for docs/progress_dashboard.md."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path


@dataclass(frozen=True)
class ProgressDashboardDomainRow:
    domain: str
    weight: int
    completed: int
    total: int
    progress_pct: int


@dataclass(frozen=True)
class ProgressDashboardSectionCount:
    domain: str
    completed: int
    total: int
    checked_items: int
    unchecked_items: int


@dataclass(frozen=True)
class ProgressDashboardConsistencyIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class ProgressDashboardConsistencyResult:
    path: str
    ok: bool
    weighted_reference_pct: int | None
    computed_weighted_pct: int
    domain_rows: tuple[ProgressDashboardDomainRow, ...]
    section_counts: tuple[ProgressDashboardSectionCount, ...]
    issues: tuple[ProgressDashboardConsistencyIssue, ...]


_DOMAIN_ROW_RE = re.compile(r"^\| (?P<domain>.+?) \| (?P<weight>\d+) \| (?P<done>\d+) \| (?P<total>\d+) \| (?P<pct>\d+)% \|$")
_SECTION_RE = re.compile(r"^### (?P<domain>.+?)（(?P<done>\d+)/(?P<total>\d+)）$")
_WEIGHTED_RE = re.compile(r"約 \*\*(?P<pct>\d+)%\*\*")


def _parse_domain_rows(lines: list[str]) -> tuple[ProgressDashboardDomainRow, ...]:
    rows: list[ProgressDashboardDomainRow] = []
    for line in lines:
        match = _DOMAIN_ROW_RE.match(line.strip())
        if not match:
            continue
        rows.append(
            ProgressDashboardDomainRow(
                domain=match.group("domain"),
                weight=int(match.group("weight")),
                completed=int(match.group("done")),
                total=int(match.group("total")),
                progress_pct=int(match.group("pct")),
            )
        )
    return tuple(rows)


def _parse_section_counts(lines: list[str]) -> tuple[ProgressDashboardSectionCount, ...]:
    sections: list[ProgressDashboardSectionCount] = []
    current: tuple[str, int, int] | None = None
    checked = 0
    unchecked = 0

    def flush() -> None:
        nonlocal checked, unchecked, current
        if current is None:
            return
        domain, done, total = current
        sections.append(
            ProgressDashboardSectionCount(
                domain=domain,
                completed=done,
                total=total,
                checked_items=checked,
                unchecked_items=unchecked,
            )
        )
        current = None
        checked = 0
        unchecked = 0

    for line in lines:
        section_match = _SECTION_RE.match(line.strip())
        if section_match:
            flush()
            current = (
                section_match.group("domain"),
                int(section_match.group("done")),
                int(section_match.group("total")),
            )
            continue
        if current is None:
            continue
        if line.startswith("## ") or line.startswith("### "):
            flush()
            continue
        if line.startswith("- [x] "):
            checked += 1
        elif line.startswith("- [ ] "):
            unchecked += 1
    flush()
    return tuple(sections)


def _parse_weighted_reference(lines: list[str]) -> int | None:
    for line in lines:
        match = _WEIGHTED_RE.search(line)
        if match:
            return int(match.group("pct"))
    return None


def check_progress_dashboard_consistency(path: Path) -> ProgressDashboardConsistencyResult:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rows = _parse_domain_rows(lines)
    sections = _parse_section_counts(lines)
    row_by_domain = {row.domain: row for row in rows}
    section_by_domain = {section.domain: section for section in sections}
    issues: list[ProgressDashboardConsistencyIssue] = []

    if sum(row.weight for row in rows) != 100:
        issues.append(
            ProgressDashboardConsistencyIssue(
                code="weight_total_not_100",
                severity="ERROR",
                message="domain weights must sum to 100",
            )
        )

    for row in rows:
        expected_pct = round((row.completed / row.total) * 100) if row.total else 0
        if row.progress_pct != expected_pct:
            issues.append(
                ProgressDashboardConsistencyIssue(
                    code="domain_progress_pct_mismatch",
                    severity="ERROR",
                    message=f"{row.domain}: table progress {row.progress_pct}% != computed {expected_pct}%",
                )
            )
        section = section_by_domain.get(row.domain)
        if section is None:
            issues.append(
                ProgressDashboardConsistencyIssue(
                    code="section_missing",
                    severity="ERROR",
                    message=f"{row.domain}: detail checklist section is missing",
                )
            )
            continue
        if (section.completed, section.total) != (row.completed, row.total):
            issues.append(
                ProgressDashboardConsistencyIssue(
                    code="section_header_table_mismatch",
                    severity="ERROR",
                    message=(
                        f"{row.domain}: section header {section.completed}/{section.total} "
                        f"!= table {row.completed}/{row.total}"
                    ),
                )
            )
        counted_total = section.checked_items + section.unchecked_items
        if (section.checked_items, counted_total) != (section.completed, section.total):
            issues.append(
                ProgressDashboardConsistencyIssue(
                    code="section_checkbox_count_mismatch",
                    severity="ERROR",
                    message=(
                        f"{row.domain}: checkbox count {section.checked_items}/{counted_total} "
                        f"!= header {section.completed}/{section.total}"
                    ),
                )
            )

    actual_import = row_by_domain.get("Actual Import Readiness")
    actual_section = section_by_domain.get("Actual Import Readiness")
    if actual_import is None or actual_import.completed != 0 or actual_import.progress_pct != 0:
        issues.append(
            ProgressDashboardConsistencyIssue(
                code="actual_import_not_zero",
                severity="ERROR",
                message="Actual Import Readiness must remain 0% until explicit approval",
            )
        )
    if actual_section is not None and actual_section.checked_items != 0:
        issues.append(
            ProgressDashboardConsistencyIssue(
                code="actual_import_checked_items_present",
                severity="ERROR",
                message="Actual Import Readiness checklist must not contain checked items",
            )
        )

    computed_weighted = round(sum(row.weight * row.completed / row.total for row in rows if row.total))
    weighted_reference = _parse_weighted_reference(lines)
    if weighted_reference is not None and weighted_reference != computed_weighted:
        issues.append(
            ProgressDashboardConsistencyIssue(
                code="weighted_reference_mismatch",
                severity="ERROR",
                message=f"weighted reference {weighted_reference}% != computed {computed_weighted}%",
            )
        )

    return ProgressDashboardConsistencyResult(
        path=str(path),
        ok=not issues,
        weighted_reference_pct=weighted_reference,
        computed_weighted_pct=computed_weighted,
        domain_rows=rows,
        section_counts=sections,
        issues=tuple(issues),
    )


def format_progress_dashboard_consistency_json(result: ProgressDashboardConsistencyResult) -> str:
    payload = {
        "path": result.path,
        "ok": result.ok,
        "weighted_reference_pct": result.weighted_reference_pct,
        "computed_weighted_pct": result.computed_weighted_pct,
        "domain_rows": [row.__dict__ for row in result.domain_rows],
        "section_counts": [section.__dict__ for section in result.section_counts],
        "issues": [issue.__dict__ for issue in result.issues],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_progress_dashboard_consistency_markdown(result: ProgressDashboardConsistencyResult) -> str:
    lines = [
        "# Progress Dashboard Consistency Check",
        "",
        f"- path: `{result.path}`",
        f"- ok: {str(result.ok).lower()}",
        f"- weighted_reference_pct: {result.weighted_reference_pct}",
        f"- computed_weighted_pct: {result.computed_weighted_pct}",
        "",
        "## Domain Rows",
        "",
        "| domain | weight | completed | total | progress |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result.domain_rows:
        lines.append(f"| {row.domain} | {row.weight} | {row.completed} | {row.total} | {row.progress_pct}% |")
    lines.extend(["", "## Issues"])
    if result.issues:
        lines.extend(f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in result.issues)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Safety Notes",
            "- source-only markdown consistency check",
            "- no live HTTP / cache write / actual import / broker API / raw Excel parsing",
            "- no workflow change / workflow_dispatch / env secret display / trading action / real email send",
            "",
        ]
    )
    return "\n".join(lines)
