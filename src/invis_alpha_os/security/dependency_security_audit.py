"""Dependency inventory audit without adding new packages."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class DependencySecurityAuditResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tool_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _installed_packages() -> list[dict[str, str]]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    return [{"name": str(row.get("name", "")), "version": str(row.get("version", ""))} for row in raw if isinstance(row, dict)]


def build_dependency_security_audit() -> DependencySecurityAuditResult:
    packages = _installed_packages()
    pip_audit_available = _tool_available("pip_audit")
    vulnerable_count: int | None = None
    audit_note = "pip_audit not installed; inventory only"
    if pip_audit_available:
        audit_note = "pip_audit available but not executed (no network in default audit)"

    payload = {
        "overall_status": "inventory_only",
        "generated_at": _now_iso(),
        "python_version": sys.version.split()[0],
        "installed_package_count": len(packages),
        "packages_sample": packages[:30],
        "pip_audit_available": pip_audit_available,
        "vulnerable_count": vulnerable_count,
        "audit_note": audit_note,
        "no_new_dependencies": True,
        "secrets_printed": False,
    }
    lines = [
        "# Dependency Security Audit",
        "",
        "- overall_status: inventory_only",
        f"- python_version: {payload['python_version']}",
        f"- installed_package_count: {len(packages)}",
        f"- pip_audit_available: {str(pip_audit_available).lower()}",
        f"- audit_note: {audit_note}",
        "",
    ]
    return DependencySecurityAuditResult(markdown_text="\n".join(lines), json_payload=payload)
