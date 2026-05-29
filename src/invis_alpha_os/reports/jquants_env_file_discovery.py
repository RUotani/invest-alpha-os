"""Discover J-Quants env-file candidates and key presence (no secret values)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.env_file_loader import (
    JQUANTS_ENV_ALLOWLIST,
    _ENV_LINE_RE,
    parse_allowlisted_env_file,
)
from invis_alpha_os.config.paths import ROOT_DIR

REQUIRED_JQUANTS_KEYS: tuple[str, ...] = (
    "JQUANTS_ENABLED",
    "JQUANTS_API_BASE_URL",
    "JQUANTS_API_KEY",
)

OPTIONAL_JQUANTS_KEYS: tuple[str, ...] = (
    "JQUANTS_ALLOW_LIVE_HTTP",
    "JQUANTS_DATA_AVAILABLE_FROM",
    "JQUANTS_DATA_AVAILABLE_TO",
)

DEFAULT_ENV_CANDIDATE_RELATIVE_PATHS: tuple[str, ...] = (
    ".env",
    ".env.local",
    "config/.env",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _redacted_path_label(path: Path) -> str:
    try:
        rel = path.expanduser().resolve().relative_to(Path.home())
        return str(rel).replace("\\", "/")
    except ValueError:
        return "outside_home"


def default_env_candidate_paths(*, repo_root: Path | None = None) -> list[Path]:
    root = repo_root or ROOT_DIR
    home = Path.home()
    candidates = [
        root / ".env",
        root / ".env.local",
        root / "config" / ".env",
        home / "repos" / "invest-alpha-os" / ".env",
        home / "repos" / "invest-alpha-os" / ".env.local",
        home / "Downloads" / "jquants.env",
        home / "Documents" / "jquants.env",
    ]
    seen: set[Path] = set()
    out: list[Path] = []
    for path in candidates:
        resolved = path.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(resolved)
    return out


def inspect_env_file_keys(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "exists": False,
            "path_redacted_label": _redacted_path_label(path),
            "keys": {},
        }
    text = path.read_text(encoding="utf-8")
    parsed = parse_allowlisted_env_file(text)
    all_keys_in_file: list[str] = []
    for line in text.splitlines():
        match = _ENV_LINE_RE.match(line)
        if match:
            all_keys_in_file.append(match.group(1))
    key_status: dict[str, str] = {}
    for key in sorted(set(all_keys_in_file)):
        if key in JQUANTS_ENV_ALLOWLIST:
            value = parsed.get(key, "")
            key_status[key] = "present_nonempty" if value.strip() else "present_empty"
        else:
            key_status[key] = "ignored_not_allowlisted"
    return {
        "exists": True,
        "path_redacted_label": _redacted_path_label(path),
        "keys": key_status,
        "allowlisted_keys_found": sorted(k for k in parsed.keys()),
    }


def merge_env_for_preflight(*, env_file: Path | None) -> dict[str, str]:
    merged = dict(os.environ)
    if env_file is not None and env_file.is_file():
        parsed = parse_allowlisted_env_file(env_file.read_text(encoding="utf-8"))
        merged.update(parsed)
    return merged


@dataclass(frozen=True)
class JQuantsEnvFileDiscoveryResult:
    markdown_text: str
    json_payload: dict[str, Any]
    selected_env_file: Path | None


def build_jquants_env_file_discovery(
    *,
    report_date: str,
    repo_root: Path | None = None,
) -> JQuantsEnvFileDiscoveryResult:
    candidates_info: list[dict[str, Any]] = []
    selected: Path | None = None
    for path in default_env_candidate_paths(repo_root=repo_root):
        info = inspect_env_file_keys(path)
        info["candidate_path_redacted"] = info["path_redacted_label"]
        candidates_info.append(info)
        if selected is None and info.get("exists"):
            allowlisted = info.get("allowlisted_keys_found") or []
            if any(k in allowlisted for k in REQUIRED_JQUANTS_KEYS):
                selected = path

    key_table: list[dict[str, str]] = []
    if selected is not None:
        inspection = inspect_env_file_keys(selected)
        for key in list(REQUIRED_JQUANTS_KEYS) + list(OPTIONAL_JQUANTS_KEYS):
            status = inspection["keys"].get(key, "absent")
            key_table.append({"key": key, "status": status})
    else:
        for key in list(REQUIRED_JQUANTS_KEYS) + list(OPTIONAL_JQUANTS_KEYS):
            key_table.append({"key": key, "status": "absent"})

    required_present = all(
        row["status"] == "present_nonempty"
        for row in key_table
        if row["key"] in REQUIRED_JQUANTS_KEYS
    )
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "candidates": candidates_info,
        "selected_env_file_redacted": _redacted_path_label(selected) if selected else None,
        "required_keys_present": required_present,
        "key_presence": key_table,
        "missing_required_keys": [
            row["key"]
            for row in key_table
            if row["key"] in REQUIRED_JQUANTS_KEYS and row["status"] != "present_nonempty"
        ],
        "secrets_printed": False,
    }
    lines = [
        "# J-Quants Env-file Discovery",
        "",
        f"- selected_env_file_redacted: {payload['selected_env_file_redacted'] or 'none'}",
        f"- required_keys_present: {str(required_present).lower()}",
        "",
        "## Candidates",
        "",
        "| path_redacted | exists |",
        "| --- | --- |",
    ]
    for row in candidates_info:
        lines.append(f"| {row.get('path_redacted_label', '-')} | {str(row.get('exists', False)).lower()} |")
    lines.extend(["", "## Key presence (selected file)", "", "| key | status |", "| --- | --- |"])
    for row in key_table:
        lines.append(f"| {row['key']} | {row['status']} |")
    lines.append("")
    return JQuantsEnvFileDiscoveryResult(
        markdown_text="\n".join(lines),
        json_payload=payload,
        selected_env_file=selected,
    )
