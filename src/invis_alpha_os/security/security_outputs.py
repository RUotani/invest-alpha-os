"""Write and sync redacted security audit outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_security_outputs(
    *,
    out_dir: Path,
    report_date: str,
    basename: str,
    markdown_text: str,
    json_payload: dict[str, Any],
    write_latest: bool,
    write_archive: bool,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    yyyy = report_date[:4]
    if write_latest:
        latest = out_dir / "latest"
        latest.mkdir(parents=True, exist_ok=True)
        md = latest / f"{basename}.md"
        js = latest / f"{basename}.json"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"latest_{basename}_md"] = md
        paths[f"latest_{basename}_json"] = js
    if write_archive:
        arc = out_dir / "archive" / yyyy / report_date
        arc.mkdir(parents=True, exist_ok=True)
        md = arc / f"{basename}.md"
        js = arc / f"{basename}.json"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"archive_{basename}_md"] = md
        paths[f"archive_{basename}_json"] = js
    return paths


def sync_security_outputs_to_reports_repo(
    *,
    reports_repo_path: Path,
    repo_root: Path,
    report_date: str,
    basename: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    if reports_repo_path.resolve() == repo_root.resolve():
        raise ValueError("reports-repo-path must differ from source repo")
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for root, label in ((latest, "reports_latest"), (weekly, "reports_weekly")):
        md = root / f"{basename}.md"
        js = root / f"{basename}.json"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"{label}_{basename}_md"] = md
        paths[f"{label}_{basename}_json"] = js
    return paths
