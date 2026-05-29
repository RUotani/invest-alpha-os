"""Safe allowlisted env-file loader for J-Quants CLI (no secrets printed)."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

JQUANTS_ENV_ALLOWLIST: frozenset[str] = frozenset(
    {
        "JQUANTS_ENABLED",
        "JQUANTS_API_BASE_URL",
        "JQUANTS_API_KEY",
        "JQUANTS_ALLOW_LIVE_HTTP",
        "JQUANTS_DATA_AVAILABLE_FROM",
        "JQUANTS_DATA_AVAILABLE_TO",
    }
)

_ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


@dataclass(frozen=True)
class EnvFileLoadResult:
    env_file_path: str
    keys_loaded: tuple[str, ...]
    keys_skipped_existing: tuple[str, ...]
    keys_ignored: tuple[str, ...]


class EnvFileLoaderError(ValueError):
    """Raised when env-file loading is refused or the file is invalid."""


def _strip_inline_comment(value: str) -> str:
    for idx, char in enumerate(value):
        if char == "#" and idx > 0 and value[idx - 1].isspace():
            return value[:idx].rstrip()
    return value.rstrip()


def _parse_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return _strip_inline_comment(value)


def parse_allowlisted_env_file(text: str, *, allowlist: frozenset[str] = JQUANTS_ENV_ALLOWLIST) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(line)
        if not match:
            continue
        key = match.group(1)
        if key not in allowlist:
            continue
        parsed[key] = _parse_env_value(match.group(2))
    return parsed


def is_git_tracked(path: Path, repo_root: Path) -> bool:
    resolved = path.resolve()
    root = repo_root.resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(rel)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def apply_allowlisted_env_file(
    env_file: Path,
    *,
    repo_root: Path,
    allowlist: frozenset[str] = JQUANTS_ENV_ALLOWLIST,
) -> EnvFileLoadResult:
    resolved = env_file.expanduser().resolve()
    if not resolved.is_file():
        raise EnvFileLoaderError(f"env file not found: {resolved}")
    if is_git_tracked(resolved, repo_root):
        raise EnvFileLoaderError(
            f"refusing git-tracked env file: {resolved.name} (use an untracked local secrets file)"
        )

    text = resolved.read_text(encoding="utf-8")
    parsed = parse_allowlisted_env_file(text, allowlist=allowlist)
    all_keys_in_file: list[str] = []
    for line in text.splitlines():
        match = _ENV_LINE_RE.match(line)
        if match:
            all_keys_in_file.append(match.group(1))
    keys_ignored = tuple(dict.fromkeys(key for key in all_keys_in_file if key not in allowlist))
    keys_loaded: list[str] = []
    keys_skipped_existing: list[str] = []
    for key, value in parsed.items():
        if key in os.environ:
            keys_skipped_existing.append(key)
            continue
        os.environ[key] = value
        keys_loaded.append(key)

    return EnvFileLoadResult(
        env_file_path=str(resolved),
        keys_loaded=tuple(dict.fromkeys(keys_loaded)),
        keys_skipped_existing=tuple(dict.fromkeys(keys_skipped_existing)),
        keys_ignored=tuple(dict.fromkeys(keys_ignored)),
    )


def env_file_load_metadata(result: EnvFileLoadResult) -> dict[str, object]:
    return {
        "env_file_used": True,
        "env_file_path": result.env_file_path,
        "keys_loaded_from_file": list(result.keys_loaded),
        "keys_skipped_existing": list(result.keys_skipped_existing),
        "keys_ignored_not_allowlisted": list(result.keys_ignored),
    }
