"""Evidence manifest writer for git-external outputs (read-only metadata to repo)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_evidence_manifest(
    *,
    task_id: str,
    evidence_path: Path,
    command: str,
    result: str,
    summary: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build manifest dict (no secret values)."""

    size_bytes: int | None = None
    sha256: str | None = None
    if evidence_path.is_file():
        size_bytes = evidence_path.stat().st_size
        sha256 = _sha256_file(evidence_path)

    payload: dict[str, Any] = {
        "task_id": task_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_path": str(evidence_path),
        "size_bytes": size_bytes,
        "sha256": sha256,
        "command": command,
        "result": result,
        "summary": summary,
        "secret_free": True,
        "observation_only": True,
    }
    if extra:
        payload.update(extra)
    return payload


def format_evidence_manifest_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        f"# Evidence Manifest — {manifest.get('task_id', 'unknown')}",
        "",
        f"**generated_at**: {manifest.get('generated_at', '')}",
        "**secret-free**: yes",
        "",
        "| 項目 | 値 |",
        "| --- | --- |",
        f"| evidence path | `{manifest.get('evidence_path', '')}` |",
        f"| size_bytes | {manifest.get('size_bytes')} |",
        f"| sha256 | `{manifest.get('sha256')}` |",
        f"| command | `{manifest.get('command', '')}` |",
        f"| result | `{manifest.get('result', '')}` |",
    ]
    for key in sorted(manifest.keys()):
        if key in {
            "task_id",
            "generated_at",
            "evidence_path",
            "size_bytes",
            "sha256",
            "command",
            "result",
            "summary",
            "secret_free",
            "observation_only",
        }:
            continue
        lines.append(f"| {key} | {manifest.get(key)} |")
    lines.extend(["", "## Summary", "", str(manifest.get("summary") or ""), ""])
    return "\n".join(lines)


def write_evidence_manifest_report(
    manifest: dict[str, Any],
    *,
    path_base: Path | None = None,
    report_date: str | None = None,
) -> Path:
    """Write manifest markdown under reports/YYYY-MM-DD/ (repo-safe)."""

    root = path_base or ROOT_DIR
    day = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    task_id = str(manifest.get("task_id") or "unknown")
    out_dir = root / "reports" / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"evidence_manifest_{task_id}.md"
    out_path.write_text(format_evidence_manifest_markdown(manifest), encoding="utf-8")
    return out_path
