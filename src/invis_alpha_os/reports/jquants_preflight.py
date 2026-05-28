"""Read-only J-Quants credential preflight (no secrets, no live HTTP)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class JQuantsPreflightResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_present(env: dict[str, str], key: str) -> bool:
    return bool(str(env.get(key, "")).strip())


def _env_truthy(env: dict[str, str], key: str) -> bool:
    return str(env.get(key, "")).strip().lower() in {"1", "true", "yes"}


def assess_jquants_credentials(env: dict[str, str] | None = None) -> dict[str, Any]:
    values = dict(os.environ) if env is None else env
    jquants_enabled = _env_truthy(values, "JQUANTS_ENABLED")
    api_base_url_present = _env_present(values, "JQUANTS_API_BASE_URL")
    api_key_present = _env_present(values, "JQUANTS_API_KEY")
    allow_live_http = _env_truthy(values, "JQUANTS_ALLOW_LIVE_HTTP")
    missing_env: list[str] = []
    if not jquants_enabled:
        missing_env.append("JQUANTS_ENABLED")
    if not api_base_url_present:
        missing_env.append("JQUANTS_API_BASE_URL")
    if not api_key_present:
        missing_env.append("JQUANTS_API_KEY")
    refresh_allowed = jquants_enabled and api_base_url_present and api_key_present
    return {
        "jquants_enabled": jquants_enabled,
        "api_base_url_present": api_base_url_present,
        "api_key_present": api_key_present,
        "jquants_allow_live_http": allow_live_http,
        "refresh_allowed": refresh_allowed,
        "missing_env": missing_env,
        "secrets_printed": False,
        "live_http_executed": False,
        "cache_write_executed": False,
    }


def build_jquants_preflight(*, report_date: str, env: dict[str, str] | None = None) -> JQuantsPreflightResult:
    diag = assess_jquants_credentials(env)
    payload = {"report_date": report_date, "generated_at": _now_iso(), **diag}
    lines = [
        "# J-Quants Preflight",
        "",
        "## メタ情報",
        f"- report_date: {report_date}",
        f"- generated_at: {payload['generated_at']}",
        f"- jquants_enabled: {str(diag['jquants_enabled']).lower()}",
        f"- api_base_url_present: {str(diag['api_base_url_present']).lower()}",
        f"- api_key_present: {str(diag['api_key_present']).lower()}",
        f"- refresh_allowed: {str(diag['refresh_allowed']).lower()}",
        "- secrets_printed: false",
        "- live_http_executed: false",
        "- cache_write_executed: false",
        "",
        "## 不足env",
    ]
    if diag["missing_env"]:
        for key in diag["missing_env"]:
            lines.append(f"- {key}: absent")
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## 次アクション",
            "- refresh_allowed=false の場合は J-Quants env を設定して preflight を再実行",
            "- refresh_allowed=true の場合のみ gated execute refresh を1回実行",
            "",
        ]
    )
    return JQuantsPreflightResult(markdown_text="\n".join(lines), json_payload=payload)
