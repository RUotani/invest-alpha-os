"""Read-only GitHub API helpers for security evidence (no settings mutation)."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def owner_repo(repo: str) -> tuple[str, str]:
    owner, name = repo.split("/", 1)
    return owner, name


def gh_api_json(path: str) -> dict[str, Any] | None:
    try:
        proc = subprocess.run(
            ["gh", "api", path],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def gh_api_list(path: str) -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            ["gh", "api", path],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def gh_api_status(path: str, *, method: str = "GET") -> int | None:
    try:
        proc = subprocess.run(
            ["gh", "api", "-X", method, path, "-i"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    for line in proc.stdout.splitlines():
        if line.startswith("HTTP/"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
    return None
