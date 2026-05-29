"""Discover local manual/broker JP bars CSV candidates (paths redacted in reports)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.env_file_loader import is_git_tracked
from invis_alpha_os.reports.manual_csv_pii_guard import run_manual_csv_pii_guard
from invis_alpha_os.reports.manual_data_dropzone import manual_data_search_roots

CANDIDATE_FILENAMES: tuple[str, ...] = (
    "manual_jp_bars.csv",
    "jp_bars.csv",
    "jp_daily_bars.csv",
    "broker_jp_bars.csv",
    "moomoo_jp_bars.csv",
    "sbi_jp_bars.csv",
    "rakuten_jp_bars.csv",
)


def _search_roots() -> list[Path]:
    return manual_data_search_roots()


def _location_label(path: Path) -> str:
    try:
        rel = path.parent.relative_to(Path.home())
        return str(rel).replace("\\", "/") or "home"
    except ValueError:
        return "outside_home"


def _candidate_record(path: Path, *, repo_root: Path) -> dict[str, Any]:
    pii = run_manual_csv_pii_guard(path)
    tracked = is_git_tracked(path, repo_root)
    safe = (
        pii.status == "passed"
        and not pii.account_data_detected
        and not tracked
        and path.is_file()
    )
    return {
        "filename": path.name,
        "path_redacted": True,
        "location_label": _location_label(path),
        "git_tracked": tracked,
        "pii_guard_status": pii.status,
        "account_data_detected": pii.account_data_detected,
        "safe_to_validate": safe,
        "resolved_path": str(path.resolve()),
    }


@dataclass(frozen=True)
class ManualCsvDiscoveryResult:
    markdown_text: str
    json_payload: dict[str, Any]
    selected_path: Path | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_manual_csv_candidates(*, repo_root: Path) -> list[dict[str, Any]]:
    seen: set[Path] = set()
    found: list[dict[str, Any]] = []
    for root in _search_roots():
        if not root.is_dir():
            continue
        for name in CANDIDATE_FILENAMES:
            path = (root / name).resolve()
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            found.append(_candidate_record(path, repo_root=repo_root))
        try:
            for path in sorted(root.glob("*.csv")):
                resolved = path.resolve()
                if resolved in seen or resolved.name not in CANDIDATE_FILENAMES:
                    continue
                seen.add(resolved)
                found.append(_candidate_record(resolved, repo_root=repo_root))
        except OSError:
            continue
    found.sort(key=lambda row: (not row["safe_to_validate"], row["filename"]))
    return found


def _public_payload(candidates: list[dict[str, Any]], selected: dict[str, Any] | None) -> dict[str, Any]:
    public_candidates = []
    for row in candidates:
        public_candidates.append({k: v for k, v in row.items() if k != "resolved_path"})
    selected_public = None
    if selected is not None:
        selected_public = {k: v for k, v in selected.items() if k != "resolved_path"}
    return {
        "csv_candidates_found": len(candidates),
        "candidates": public_candidates,
        "selected_candidate": selected_public,
        "safe_to_validate": bool(selected and selected.get("safe_to_validate")),
    }


def build_manual_csv_discovery(*, report_date: str, repo_root: Path) -> ManualCsvDiscoveryResult:
    candidates = discover_manual_csv_candidates(repo_root=repo_root)
    selected = next((row for row in candidates if row.get("safe_to_validate")), None)
    if selected is None and candidates:
        selected = candidates[0]
    payload = _public_payload(candidates, selected)
    payload["report_date"] = report_date
    payload["generated_at"] = _now_iso()
    lines = [
        "# Manual CSV Discovery",
        "",
        f"- csv_candidates_found: {payload['csv_candidates_found']}",
        f"- safe_to_validate: {str(payload['safe_to_validate']).lower()}",
        "",
    ]
    if selected:
        lines.extend(
            [
                "## Selected candidate",
                "",
                f"- filename: {selected.get('filename', '-')}",
                f"- location_label: {selected.get('location_label', '-')}",
                f"- pii_guard_status: {selected.get('pii_guard_status', '-')}",
                f"- account_data_detected: {str(selected.get('account_data_detected', False)).lower()}",
                f"- git_tracked: {str(selected.get('git_tracked', False)).lower()}",
                "",
            ]
        )
    else:
        lines.append("- selected_candidate: none\n")
    selected_path = None
    if selected and selected.get("safe_to_validate"):
        selected_path = Path(str(selected["resolved_path"]))
    return ManualCsvDiscoveryResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        selected_path=selected_path,
    )
