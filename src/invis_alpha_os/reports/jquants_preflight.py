"""Read-only J-Quants credential preflight (no secrets, no live HTTP)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from invis_alpha_os.config.env_bool import general_env_truthy, provider_allow_flag_truthy
from invis_alpha_os.data.adapters.jquants_client import (
    JQuantsClient,
    _blank_to_none,
    _resolve_jquants_api_version,
    _truthy_flag,
)
from invis_alpha_os.reports.jquants_date_range import resolve_refresh_date_range


@dataclass(frozen=True)
class JQuantsPreflightResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env_present(env: dict[str, str], key: str) -> bool:
    return bool(str(env.get(key, "")).strip())


def assess_jquants_base_url(env: dict[str, str]) -> dict[str, Any]:
    raw = str(env.get("JQUANTS_API_BASE_URL", "")).strip()
    present = bool(raw)
    parseable = False
    has_scheme = False
    host_present = False
    if present:
        parsed = urlparse(raw)
        parseable = True
        has_scheme = parsed.scheme in {"http", "https"}
        host_present = bool(parsed.netloc)
    return {
        "api_base_url_parseable": parseable,
        "api_base_url_has_scheme": has_scheme,
        "api_base_url_host_present": host_present,
        "api_base_url_redacted": True,
    }


def build_jquants_client_from_env_map(env: dict[str, str]) -> JQuantsClient:
    api_disp, api_eff = _resolve_jquants_api_version(env.get("JQUANTS_API_VERSION"))
    return JQuantsClient(
        base_url=_blank_to_none(env.get("JQUANTS_API_BASE_URL")),
        api_version=api_disp,
        api_version_effective=api_eff,
        enabled=_truthy_flag(env.get("JQUANTS_ENABLED"), default="false"),
        api_key=_blank_to_none(env.get("JQUANTS_API_KEY")),
        email=_blank_to_none(env.get("JQUANTS_EMAIL")),
        password=_blank_to_none(env.get("JQUANTS_PASSWORD")),
        refresh_token=_blank_to_none(env.get("JQUANTS_REFRESH_TOKEN")),
        id_token=_blank_to_none(env.get("JQUANTS_ID_TOKEN")),
    )


def assess_jquants_endpoint_contract(env: dict[str, str]) -> dict[str, Any]:
    client = build_jquants_client_from_env_map(env)
    endpoint_path_configured = False
    if client.api_version_effective == "v2" and client.has_base_url():
        preview = client.build_v2_daily_bars_request_preview(
            "5802",
            from_date="2026-01-02",
            to_date="2026-01-03",
        )
        endpoint_path_configured = preview.get("status") == "ok"
    return {
        "endpoint_category": "daily_bars",
        "endpoint_path_configured": endpoint_path_configured,
        "endpoint_path_redacted": True,
    }


def assess_jquants_credentials(env: dict[str, str] | None = None) -> dict[str, Any]:
    values = dict(os.environ) if env is None else env
    jquants_enabled = general_env_truthy(values.get("JQUANTS_ENABLED"))
    api_base_url_present = _env_present(values, "JQUANTS_API_BASE_URL")
    api_key_present = _env_present(values, "JQUANTS_API_KEY")
    allow_live_http = provider_allow_flag_truthy(values.get("JQUANTS_ALLOW_LIVE_HTTP"))
    missing_env: list[str] = []
    if not jquants_enabled:
        missing_env.append("JQUANTS_ENABLED")
    if not api_base_url_present:
        missing_env.append("JQUANTS_API_BASE_URL")
    if not api_key_present:
        missing_env.append("JQUANTS_API_KEY")
    refresh_allowed = jquants_enabled and api_base_url_present and api_key_present
    base_url_diag = assess_jquants_base_url(values)
    endpoint_diag = assess_jquants_endpoint_contract(values)
    date_range_diag = resolve_refresh_date_range(values, allow_date_clamp=True).as_dict()
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
        **base_url_diag,
        **endpoint_diag,
        **date_range_diag,
    }


def build_jquants_preflight(
    *,
    report_date: str,
    env: dict[str, str] | None = None,
    env_file_meta: dict[str, object] | None = None,
) -> JQuantsPreflightResult:
    diag = assess_jquants_credentials(env)
    payload: dict[str, Any] = {"report_date": report_date, "generated_at": _now_iso(), **diag}
    if env_file_meta:
        payload.update(env_file_meta)
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
        f"- api_base_url_parseable: {str(diag['api_base_url_parseable']).lower()}",
        f"- api_base_url_has_scheme: {str(diag['api_base_url_has_scheme']).lower()}",
        f"- api_base_url_host_present: {str(diag['api_base_url_host_present']).lower()}",
        f"- endpoint_path_configured: {str(diag['endpoint_path_configured']).lower()}",
        f"- data_available_to_present: {str(diag.get('data_available_to_present', False)).lower()}",
        f"- requested_to_date: {diag.get('requested_to_date', '-')}",
        f"- requested_to_date_within_contract: {str(diag.get('requested_to_date_within_contract', False)).lower()}",
        f"- date_range_clamp_required: {str(diag.get('date_range_clamp_required', False)).lower()}",
        f"- clamped_to_date: {diag.get('clamped_to_date', '-')}",
        "- secrets_printed: false",
        "- live_http_executed: false",
        "- cache_write_executed: false",
    ]
    if env_file_meta and env_file_meta.get("env_file_used"):
        loaded_keys = env_file_meta.get("keys_loaded_from_file", [])
        loaded_label = (
            ", ".join(str(key) for key in loaded_keys)
            if isinstance(loaded_keys, list) and loaded_keys
            else "(none)"
        )
        lines.extend(
            [
                "- env_file_used: true",
                f"- keys_loaded_from_file: {loaded_label}",
            ]
        )
    lines.extend(
        [
            "",
            "## 不足env",
        ]
    )
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
