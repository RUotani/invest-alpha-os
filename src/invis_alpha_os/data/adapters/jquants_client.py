"""J-Quants API client (Phase 1a Task 2–4.2, safety-hardened).

Live HTTP for **Version 2** (primary) occurs only when **all** of:

- ``JQUANTS_ENABLED=true``
- Caller passes ``attempt_live=True`` (e.g. ``--live`` on the debug CLI)
- Environment variable ``JQUANTS_ALLOW_LIVE_HTTP=true``
- ``JQUANTS_API_BASE_URL`` is set (non-empty)
- ``JQUANTS_API_KEY`` is set (non-empty): request uses ``x-api-key`` header (**never** surfaced in CLI dict)

Version **1** (legacy) retains refresh/id bearer flows behind ``JQUANTS_API_VERSION=v1`` only.

Public return dicts **omit secrets** (API key, tokens, passwords, raw auth bodies).

For **V2 live** ``daily_quotes``, HTTP 200 alone is not treated as success: the JSON object must normalize via
``normalize_v2_daily_bars_response``: one of ``data`` / ``daily_quotes`` / ``bars`` / ``results`` must hold a **list**
(Phase 1a Task 5). Dict or string bodies under those keys are ``invalid_response``; empty list is ``success``
with ``row_count=0``.

**V2** ``GET …/equities/bars/daily`` query uses only ``code``, ``date``, ``from``, ``to`` (never ``from_date`` /
``to_date``). Date values are sent as ``YYYY-MM-DD`` (Task 5.1). Base URLs that already end with ``/v2`` are
joined with paths like ``/equities/bars/daily`` so ``/v2/v2`` is not produced (Task 5.2). Use
``build_v2_daily_bars_request_preview`` / ``--preview-request`` to inspect URLs without HTTP or secrets.

``debug jquants-status`` must never perform HTTP — use ``safe_auth_status()`` only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

# V2 daily bars: scan in this order; first present key must map to a list (Task 5).
_V2_DAILY_QUOTES_BODY_KEYS: tuple[str, ...] = ("data", "daily_quotes", "bars", "results")


def _format_v2_daily_bars_date_query(value: str) -> str:
    """Format ``date`` / ``from`` / ``to`` query values for V2 daily bars (YYYY-MM-DD).

    Accepts ``YYYY-MM-DD`` or a compact ``YYYYMMDD`` string; wire format is always ``YYYY-MM-DD``.
    """

    s = (value or "").strip()
    if not s:
        return s
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return s


def _join_v2_base_and_path(base_url: str, path: str) -> str:
    """Join base URL with a path segment, avoiding duplicated ``/v2`` when both include it."""

    base = (base_url or "").rstrip("/")
    p = path if path.startswith("/") else f"/{path}"
    if base.endswith("/v2") and p.startswith("/v2/"):
        p = p[3:]
        if not p.startswith("/"):
            p = f"/{p}"
    return f"{base}{p}"


def normalize_v2_daily_bars_response(payload: dict) -> dict[str, Any]:
    """Normalize a V2-equities daily-bars-style JSON body (no raw API payload in return).

    - Accepts only ``payload`` that is already a JSON object (``dict``). Callers handle non-dict /
      top-level array / decode errors separately.
    - Looks for array data under keys **in order**: ``data``, ``daily_quotes``, ``bars``, ``results``.
    - The **first key that exists** must map to a **list** (may be empty). Non-list → ``invalid_response``.
    - Absent keys are skipped until one is present; if none of the four exist → ``invalid_response``.
    Returns only: ``success`` + ``row_count`` + ``source_key``, or ``invalid_response`` + ``reason``.
    Never includes API keys, tokens, passwords, or raw responses.
    """

    if not isinstance(payload, dict):
        return {"status": "invalid_response", "reason": "payload_not_dict"}

    for key in _V2_DAILY_QUOTES_BODY_KEYS:
        if key not in payload:
            continue
        val = payload[key]
        if isinstance(val, list):
            return {"status": "success", "row_count": len(val), "source_key": key}
        return {"status": "invalid_response", "reason": f"{key}_not_list"}

    return {"status": "invalid_response", "reason": "missing_list_field"}


def _resolve_jquants_api_version(raw: str | None) -> tuple[str, str | None]:
    """Return ``(display_str, effective_label)`` where ``effective_label`` is ``v1``, ``v2``, or ``None``."""

    s = _blank_to_none(raw)
    if s is None:
        return "v2", "v2"
    t = raw.strip() if raw is not None else "v2"
    tl = t.lower()
    if tl in {"1", "v1", "version1"}:
        return t, "v1"
    if tl in {"2", "v2", "version2"}:
        return t, "v2"
    return t, None


def _paths_for_version(version_label: str) -> dict[str, str]:
    """Relative paths under ``base_url`` (official V2 shape for primary)."""

    v1_legacy = {
        "listed_master": "/listed/info",
        "auth_user": "/token/auth_user",
        "auth_refresh": "/token/auth_refresh",
        "daily_quotes": "/prices/daily_quotes",
    }
    if version_label == "v1":
        return v1_legacy
    if version_label == "v2":
        return {
            "listed_master": "/equities/master",
            "auth_user": "/token/auth_user",
            "auth_refresh": "/token/auth_refresh",
            "daily_quotes": "/equities/bars/daily",
            "bars_daily_am": "/equities/bars/daily/am",
            "investor_types": "/equities/investor-types",
            "margin_interest": "/markets/margin-interest",
        }
    raise ValueError(f"unexpected J-Quants API version label: {version_label!r}")


def _truthy_flag(value: str | None, default: str = "false") -> bool:
    return (value if value is not None else default).strip().lower() in {"1", "true", "yes", "on"}


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


class JQuantsClient:
    """J-Quants client: Version 2 primary (API Key + ``x-api-key``), Version 1 legacy (bearer tokens)."""

    def __init__(
        self,
        *,
        base_url: str | None,
        api_version: str,
        api_version_effective: str | None,
        enabled: bool,
        api_key: str | None = None,
        email: str | None = None,
        password: str | None = None,
        refresh_token: str | None = None,
        id_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_version = api_version
        self.api_version_effective = api_version_effective
        self._paths = _paths_for_version(api_version_effective) if api_version_effective else {}
        self.enabled = enabled
        self.api_key = api_key
        self.email = email
        self.password = password
        self.refresh_token = refresh_token
        self.id_token = id_token

    @classmethod
    def from_env(cls) -> JQuantsClient:
        api_disp, api_eff = _resolve_jquants_api_version(os.getenv("JQUANTS_API_VERSION"))
        base = _blank_to_none(os.getenv("JQUANTS_API_BASE_URL"))
        return cls(
            base_url=base,
            api_version=api_disp,
            api_version_effective=api_eff,
            enabled=_truthy_flag(os.getenv("JQUANTS_ENABLED"), default="false"),
            api_key=_blank_to_none(os.getenv("JQUANTS_API_KEY")),
            email=_blank_to_none(os.getenv("JQUANTS_EMAIL")),
            password=_blank_to_none(os.getenv("JQUANTS_PASSWORD")),
            refresh_token=_blank_to_none(os.getenv("JQUANTS_REFRESH_TOKEN")),
            id_token=_blank_to_none(os.getenv("JQUANTS_ID_TOKEN")),
        )

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def has_mail_password(self) -> bool:
        return bool(self.email and self.password)

    def has_refresh_token(self) -> bool:
        return bool(self.refresh_token)

    def has_id_token(self) -> bool:
        return bool(self.id_token)

    def allow_live_http_from_env(self) -> bool:
        return _truthy_flag(os.getenv("JQUANTS_ALLOW_LIVE_HTTP"), default="false")

    def is_configured(self) -> bool:
        """V2: configured when ``JQUANTS_API_KEY`` is set; V1 legacy: tokens or mail/password."""

        if self.api_version_effective == "v2":
            return self.has_api_key()
        return self.has_id_token() or self.has_refresh_token() or self.has_mail_password()

    def has_base_url(self) -> bool:
        return bool(self.base_url)

    def auth_method_safe(self) -> str:
        if self.api_version_effective == "v2":
            return "api_key"
        if self.api_version_effective == "v1":
            return "token"
        return "unknown"

    def safe_auth_status(self) -> dict[str, Any]:
        """Opaque status for ``debug jquants-status`` (no secrets, no HTTP)."""

        return {
            "api_version": self.api_version,
            "api_version_effective": self.api_version_effective,
            "unsupported_api_version": self.api_version_effective is None,
            "auth_method": self.auth_method_safe(),
            "api_key_present": self.has_api_key(),
            "base_url_present": self.has_base_url(),
            "enabled": self.is_enabled(),
            "configured": self.is_configured(),
            "email_present": bool(self.email),
            "password_present": bool(self.password),
            "refresh_token_present": bool(self.refresh_token),
            "id_token_present": bool(self.id_token),
            "allow_live_http": self.allow_live_http_from_env(),
            "token_preview": "***",
            "api_key_preview": "***",
            "raw_response_included": False,
        }

    def _unsupported_api_version_reply(self) -> dict[str, Any]:
        return {
            "status": "unsupported_version",
            "api_version": self.api_version,
            "detail": "JQUANTS_API_VERSION must be v1 or v2",
            "raw_response_included": False,
        }

    def _maybe_unsupported_api_version(self) -> dict[str, Any] | None:
        if self.api_version_effective is None:
            return self._unsupported_api_version_reply()
        return None

    def _missing_base_url_reply(self) -> dict[str, Any]:
        return self._not_configured(
            missing=["JQUANTS_API_BASE_URL"],
            reason="base_url_missing",
        )

    def _missing_api_key_reply(self) -> dict[str, Any]:
        return self._not_configured(
            missing=["JQUANTS_API_KEY"],
            reason="api_key_missing",
        )

    def _legacy_not_used_on_v2(self, *, endpoint: str) -> dict[str, Any]:
        return {
            "status": "not_applicable",
            "reason": "v2_uses_api_key",
            "endpoint": endpoint,
            "detail": "Legacy token flows require JQUANTS_API_VERSION=v1",
            "raw_response_included": False,
        }

    def _live_gate_denied_reason(self, *, cli_live_requested: bool) -> str | None:
        if not cli_live_requested:
            return None
        if not self.allow_live_http_from_env():
            return "JQUANTS_ALLOW_LIVE_HTTP is not true (required with --live)"
        return None

    def _disabled(self, *, hint: str) -> dict[str, Any]:
        return {"status": "disabled", "reason": hint, "raw_response_included": False}

    def _not_configured(self, *, missing: list[str], reason: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"status": "not_configured", "missing": missing, "raw_response_included": False}
        if reason is not None:
            out["reason"] = reason
        return out

    def _dry_run(self, *, endpoint_key: str, detail: str) -> dict[str, Any]:
        logical = self._paths.get(endpoint_key, f"/<{endpoint_key}>")
        ep = f"{self.base_url}{logical}" if self.base_url else logical
        return {
            "status": "dry_run",
            "endpoint": ep,
            "endpoint_key": endpoint_key,
            "api_version": self.api_version,
            "api_version_effective": self.api_version_effective,
            "auth_method": self.auth_method_safe(),
            "detail": detail,
            "raw_response_included": False,
        }

    def _live_blocked(self, *, reason: str) -> dict[str, Any]:
        return {"status": "live_blocked", "reason": reason, "raw_response_included": False}

    # --- Internal HTTP helpers (secrets stay in-memory only) ---
    def _post_json_uncached(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_json_bearer(self, url: str, bearer: str) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {bearer}", "Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _http_get_body(self, url: str, headers: dict[str, str]) -> str:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8")

    def _v2_daily_quotes_live_shape_error(
        self,
        *,
        status: str,
        reason: str | None = None,
        endpoint_path: str,
        code: str,
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "status": status,
            "endpoint_path": endpoint_path,
            "code": code,
            "raw_response_included": False,
            "detail": "***",
            "api_version": self.api_version,
            "api_version_effective": self.api_version_effective,
        }
        if reason is not None:
            out["reason"] = reason
        return out

    def _v2_parse_daily_quotes_live_body(
        self, raw_text: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Return ``(body_dict, None)`` on OK, or ``(None, {kind:..., reason?:...})`` on parse failure."""

        try:
            obj: Any = json.loads(raw_text)
        except json.JSONDecodeError:
            return None, {"kind": "non_json_response"}
        if isinstance(obj, list):
            return None, {"kind": "invalid_response", "reason": "top_level_array"}
        if not isinstance(obj, dict):
            return None, {"kind": "invalid_response", "reason": "not_json_object"}
        return obj, None

    def _extract_refresh_secret(self, body: dict[str, Any]) -> str | None:
        return (
            body.get("refreshToken")
            or body.get("refresh_token")
            or (body.get("token") or {}).get("refreshToken")
            or None
        )

    def _extract_id_secret(self, body: dict[str, Any]) -> str | None:
        return (
            body.get("idToken")
            or body.get("id_token")
            or (body.get("token") or {}).get("idToken")
            or None
        )

    def _require_base_for_network(self) -> dict[str, Any] | None:
        if self.has_base_url():
            return None
        return self._missing_base_url_reply()

    def _http_fetch_refresh_secret(self) -> str | None:
        if not self._paths:
            return None
        if not self.has_base_url():
            return None
        if not self.has_mail_password():
            return None
        path = self._paths["auth_user"]
        url = f"{self.base_url}{path}"
        payload = {"mailaddress": self.email, "password": self.password}
        try:
            body = self._post_json_uncached(url, payload)
        except (urllib.error.HTTPError, OSError, ValueError):
            return None
        refresh = self._extract_refresh_secret(body)
        return str(refresh) if refresh else None

    def _http_fetch_id_secret_from_refresh(self, refresh: str) -> str | None:
        if not self._paths:
            return None
        if not self.has_base_url():
            return None
        path = self._paths["auth_refresh"]
        url = f"{self.base_url}{path}"
        payload = {"refreshtoken": refresh}
        try:
            body = self._post_json_uncached(url, payload)
        except (urllib.error.HTTPError, OSError, ValueError):
            return None
        id_tok = self._extract_id_secret(body)
        return str(id_tok) if id_tok else None

    # --- Legacy V1 token APIs (still supported when ``api_version_effective == v1``) ---
    def get_refresh_token(self, *, attempt_live: bool = False) -> dict[str, Any]:
        if not self.is_enabled():
            return self._disabled(hint="JQUANTS_ENABLED=false")

        bad_ver = self._maybe_unsupported_api_version()
        if bad_ver is not None:
            return bad_ver

        if self.api_version_effective == "v2":
            return self._legacy_not_used_on_v2(endpoint="token/auth_user")

        miss = self._require_base_for_network()
        if miss is not None:
            return miss

        if not self.has_mail_password():
            return self._not_configured(missing=["JQUANTS_EMAIL", "JQUANTS_PASSWORD"])
        if not attempt_live:
            return self._dry_run(
                endpoint_key="auth_user",
                detail="Requires --live on CLI AND JQUANTS_ALLOW_LIVE_HTTP=true",
            )

        denial = self._live_gate_denied_reason(cli_live_requested=True)
        if denial:
            return self._live_blocked(reason=denial)

        refresh_secret = self._http_fetch_refresh_secret()
        if not refresh_secret:
            return {"status": "failed", "step": "auth_user", "raw_response_included": False}
        return {
            "status": "success",
            "refresh_token_obtained": True,
            "raw_response_included": False,
            "token_preview": "***",
            "api_version": self.api_version,
            "api_version_effective": self.api_version_effective,
        }

    def get_id_token(self, *, attempt_live: bool = False, refresh_override: str | None = None) -> dict[str, Any]:
        if not self.is_enabled():
            return self._disabled(hint="JQUANTS_ENABLED=false")

        bad_ver = self._maybe_unsupported_api_version()
        if bad_ver is not None:
            return bad_ver

        if self.api_version_effective == "v2":
            return self._legacy_not_used_on_v2(endpoint="token/auth_refresh")

        miss = self._require_base_for_network()
        if miss is not None:
            return miss

        refresh = refresh_override or self.refresh_token
        if not refresh:
            return self._not_configured(missing=["JQUANTS_REFRESH_TOKEN"])

        if not attempt_live:
            return self._dry_run(
                endpoint_key="auth_refresh",
                detail="Requires --live on CLI AND JQUANTS_ALLOW_LIVE_HTTP=true",
            )

        denial = self._live_gate_denied_reason(cli_live_requested=True)
        if denial:
            return self._live_blocked(reason=denial)

        id_secret = self._http_fetch_id_secret_from_refresh(refresh)
        if not id_secret:
            return {"status": "failed", "step": "auth_refresh", "raw_response_included": False}
        return {
            "status": "success",
            "id_token_obtained": True,
            "raw_response_included": False,
            "token_preview": "***",
            "api_version": self.api_version,
            "api_version_effective": self.api_version_effective,
        }

    def _resolve_bearer_secret_for_quotes_live(self) -> str | None:
        if self.id_token:
            return self.id_token
        if self.refresh_token:
            return self._http_fetch_id_secret_from_refresh(self.refresh_token)
        if self.has_mail_password():
            r = self._http_fetch_refresh_secret()
            if not r:
                return None
            return self._http_fetch_id_secret_from_refresh(r)
        return None

    def _summarize_quotes_like_payload(self, parsed: dict[str, Any]) -> tuple[str, int]:
        keys_to_try = ("daily_quotes", "quotes", "bars", "data", "items")
        for k in keys_to_try:
            val = parsed.get(k)
            if isinstance(val, list):
                row_key = (
                    "daily_quotes_row_count"
                    if k == "daily_quotes"
                    else ("quotes_row_count" if k == "quotes" else f"{k}_row_count")
                )
                return row_key, len(val)
        return "parsed_keys_count", len(parsed)

    def _v2_daily_bars_query_params(
        self,
        code: str,
        *,
        date: str | None,
        from_date: str | None,
        to_date: str | None,
    ) -> dict[str, str]:
        params: dict[str, str] = {"code": code}
        if date:
            params["date"] = _format_v2_daily_bars_date_query(date)
        if from_date:
            params["from"] = _format_v2_daily_bars_date_query(from_date)
        if to_date:
            params["to"] = _format_v2_daily_bars_date_query(to_date)
        return params

    def _v2_daily_bars_endpoint_without_query(self) -> str | None:
        if not self.base_url:
            return None
        path = self._paths.get("daily_quotes")
        if path is None:
            return None
        return _join_v2_base_and_path(self.base_url, path)

    def build_v2_daily_bars_request_preview(
        self,
        code: str,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """Describe the V2 daily-bars GET without HTTP — no secrets, no raw body, no full header mapping."""

        meta: dict[str, Any] = {
            "api_key_header_name": "x-api-key",
            "api_key_value_included": False,
            "api_key_header_present": self.has_api_key(),
        }

        bad_ver = self._maybe_unsupported_api_version()
        if bad_ver is not None:
            out = dict(bad_ver)
            out.update(meta)
            return out

        if self.api_version_effective != "v2":
            out = {
                "status": "not_applicable",
                "reason": "v2_daily_bars_preview_only",
                **meta,
            }
            return out

        if not self.has_base_url():
            return self._missing_base_url_reply() | meta

        endpoint_wo_q = self._v2_daily_bars_endpoint_without_query()
        if endpoint_wo_q is None:
            return self._missing_base_url_reply() | meta

        q_params = self._v2_daily_bars_query_params(code, date=date, from_date=from_date, to_date=to_date)
        qs = urlencode(q_params)
        return {
            "status": "ok",
            "endpoint_url_without_query": endpoint_wo_q,
            "query_params": dict(q_params),
            "full_url_without_secrets": f"{endpoint_wo_q}?{qs}",
            **meta,
        }

    def get_daily_quotes(
        self,
        code: str,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        attempt_live: bool = False,
    ) -> dict[str, Any]:
        if not self.is_enabled():
            return self._disabled(hint="JQUANTS_ENABLED=false")

        bad_ver = self._maybe_unsupported_api_version()
        if bad_ver is not None:
            return bad_ver

        miss = self._require_base_for_network()
        if miss is not None:
            return miss

        if not attempt_live:
            out = self._dry_run(
                endpoint_key="daily_quotes",
                detail=(
                    "V2 default dry-run (/equities/bars/daily). Live needs --live, "
                    "JQUANTS_ALLOW_LIVE_HTTP=true, JQUANTS_API_BASE_URL, and JQUANTS_API_KEY."
                ),
            )
            if self.api_version_effective == "v2":
                prv = self.build_v2_daily_bars_request_preview(
                    code, date=date, from_date=from_date, to_date=to_date
                )
                if prv.get("status") == "ok":
                    out["endpoint_url_without_query"] = prv["endpoint_url_without_query"]
                    out["query_params"] = prv["query_params"]
                    out["full_url_without_secrets"] = prv["full_url_without_secrets"]
                    out["api_key_header_name"] = prv["api_key_header_name"]
                    out["api_key_header_present"] = prv["api_key_header_present"]
                    out["api_key_value_included"] = False
            return out

        denial = self._live_gate_denied_reason(cli_live_requested=True)
        if denial:
            return self._live_blocked(reason=denial)

        if self.api_version_effective == "v2":
            if not self.has_api_key():
                return self._missing_api_key_reply()
            dq_path = self._paths["daily_quotes"]
            params = self._v2_daily_bars_query_params(code, date=date, from_date=from_date, to_date=to_date)
            query = urlencode(params)
            endpoint_wo_q = self._v2_daily_bars_endpoint_without_query()
            if endpoint_wo_q is None:
                return self._missing_base_url_reply()
            url = f"{endpoint_wo_q}?{query}"
            key_secret = self.api_key
            if not key_secret:
                return self._missing_api_key_reply()
            try:
                raw_body = self._http_get_body(
                    url,
                    {"x-api-key": key_secret, "Accept": "application/json"},
                )
            except urllib.error.HTTPError as e:
                prv = self.build_v2_daily_bars_request_preview(
                    code, date=date, from_date=from_date, to_date=to_date
                )
                err_out: dict[str, Any] = {
                    "status": "http_error",
                    "http_status": int(e.code),
                    "raw_response_included": False,
                    "code": code,
                    "date_from": from_date,
                    "date_to": to_date,
                    "api_key_header_name": "x-api-key",
                    "api_key_value_included": False,
                    "api_key_header_present": self.has_api_key(),
                }
                if date is not None:
                    err_out["date"] = date
                if prv.get("status") == "ok":
                    err_out["endpoint_url_without_query"] = prv["endpoint_url_without_query"]
                    err_out["query_params"] = prv["query_params"]
                    err_out["full_url_without_secrets"] = prv["full_url_without_secrets"]
                return err_out
            except OSError:
                return {"status": "error", "detail": "***", "raw_response_included": False}

            parsed, shape_err = self._v2_parse_daily_quotes_live_body(raw_body)
            if shape_err is not None:
                k = shape_err.get("kind")
                stat = "non_json_response" if k == "non_json_response" else "invalid_response"
                raw_rsn = shape_err.get("reason")
                rsn = raw_rsn if isinstance(raw_rsn, str) else None
                return self._v2_daily_quotes_live_shape_error(
                    status=stat,
                    reason=rsn,
                    endpoint_path=dq_path,
                    code=code,
                )

            assert parsed is not None
            norm = normalize_v2_daily_bars_response(parsed)
            if norm.get("status") != "success":
                rsn_raw = norm.get("reason")
                rsn = rsn_raw if isinstance(rsn_raw, str) else None
                return self._v2_daily_quotes_live_shape_error(
                    status="invalid_response",
                    reason=rsn,
                    endpoint_path=dq_path,
                    code=code,
                )

            return {
                "status": "success",
                "endpoint_path": dq_path,
                "code": code,
                "row_count": norm["row_count"],
                "source_key": norm["source_key"],
                "date_from": from_date,
                "date_to": to_date,
                "date": date,
                "raw_response_included": False,
                "api_version": self.api_version,
                "api_version_effective": self.api_version_effective,
            }

        # Legacy V1: bearer tokens
        if not (self.has_id_token() or self.has_refresh_token() or self.has_mail_password()):
            return self._not_configured(
                missing=["JQUANTS_ID_TOKEN", "JQUANTS_REFRESH_TOKEN", "(JQUANTS_EMAIL+PASSWORD)"],
            )

        bearer: str | None = self._resolve_bearer_secret_for_quotes_live()

        params = {"code": code}
        if date:
            params["date"] = date.replace("-", "")
        if from_date:
            params["from"] = from_date.replace("-", "")
        if to_date:
            params["to"] = to_date.replace("-", "")

        if not bearer:
            return {"status": "failed", "step": "resolve_bearer", "raw_response_included": False}

        query = urlencode(params)
        dq_path = self._paths["daily_quotes"]
        url = f"{self.base_url}{dq_path}?{query}"

        try:
            parsed = self._get_json_bearer(url, bearer)
        except urllib.error.HTTPError as e:
            return {
                "status": "http_error",
                "http_status": int(e.code),
                "raw_response_included": False,
            }
        except OSError:
            return {"status": "error", "detail": "***", "raw_response_included": False}

        daily = parsed.get("daily_quotes")
        quotes_list = parsed.get("quotes") if isinstance(parsed.get("quotes"), list) else None
        rows = len(daily) if isinstance(daily, list) else (len(quotes_list) if quotes_list is not None else None)
        key = (
            "daily_quotes_row_count"
            if isinstance(daily, list)
            else ("quotes_row_count" if quotes_list is not None else "parsed_keys_count")
        )
        count_val = rows if rows is not None else len(parsed)

        return {
            "status": "success",
            "endpoint_path": dq_path,
            "code": code,
            key: count_val,
            "raw_response_included": False,
            "token_preview": "***",
            "api_version": self.api_version,
            "api_version_effective": self.api_version_effective,
        }


def jquants_client_from_env() -> JQuantsClient:
    return JQuantsClient.from_env()
