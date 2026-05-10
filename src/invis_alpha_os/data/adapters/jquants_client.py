"""J-Quants API client skeleton (Phase 1a Task 2, safety-hardened).

Live HTTP occurs only when **both**:

- The caller passes ``attempt_live=True`` (e.g. ``--live`` on the debug CLI).
- Environment variable ``JQUANTS_ALLOW_LIVE_HTTP=true``.

Public return dicts intentionally **omit secrets** (tokens, passwords, raw auth bodies).

``debug jquants-status`` must never perform HTTP — use ``safe_auth_status()`` only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

DEFAULT_BASE_URL = "https://api.jquants.com/v1"


def _truthy_flag(value: str | None, default: str = "false") -> bool:
    return (value if value is not None else default).strip().lower() in {"1", "true", "yes", "on"}


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


class JQuantsClient:
    """Real-mode skeleton with strict live-http gating."""

    def __init__(
        self,
        base_url: str,
        enabled: bool,
        email: str | None = None,
        password: str | None = None,
        refresh_token: str | None = None,
        id_token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled
        self.email = email
        self.password = password
        self.refresh_token = refresh_token
        self.id_token = id_token

    @classmethod
    def from_env(cls) -> JQuantsClient:
        base = _blank_to_none(os.getenv("JQUANTS_API_BASE_URL")) or DEFAULT_BASE_URL
        return cls(
            base_url=base,
            enabled=_truthy_flag(os.getenv("JQUANTS_ENABLED"), default="false"),
            email=_blank_to_none(os.getenv("JQUANTS_EMAIL")),
            password=_blank_to_none(os.getenv("JQUANTS_PASSWORD")),
            refresh_token=_blank_to_none(os.getenv("JQUANTS_REFRESH_TOKEN")),
            id_token=_blank_to_none(os.getenv("JQUANTS_ID_TOKEN")),
        )

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def has_mail_password(self) -> bool:
        return bool(self.email and self.password)

    def has_refresh_token(self) -> bool:
        return bool(self.refresh_token)

    def has_id_token(self) -> bool:
        return bool(self.id_token)

    def allow_live_http_from_env(self) -> bool:
        return _truthy_flag(os.getenv("JQUANTS_ALLOW_LIVE_HTTP"), default="false")

    def is_configured(self) -> bool:
        return self.has_id_token() or self.has_refresh_token() or self.has_mail_password()

    def safe_auth_status(self) -> dict[str, Any]:
        """Opaque status for stderr-free `debug jquants-status` (no secrets, no HTTP)."""

        return {
            "enabled": self.is_enabled(),
            "configured": self.is_configured(),
            "email_present": bool(self.email),
            "password_present": bool(self.password),
            "refresh_token_present": bool(self.refresh_token),
            "id_token_present": bool(self.id_token),
            "allow_live_http": self.allow_live_http_from_env(),
            "token_preview": "***",
            "raw_response_included": False,
            "base_url": self.base_url,
        }

    def _live_gate_denied_reason(self, *, cli_live_requested: bool) -> str | None:
        if not cli_live_requested:
            return None
        if not self.allow_live_http_from_env():
            return "JQUANTS_ALLOW_LIVE_HTTP is not true (required with --live)"
        return None

    def _disabled(self, *, hint: str) -> dict[str, Any]:
        return {"status": "disabled", "reason": hint, "raw_response_included": False}

    def _not_configured(self, *, missing: list[str]) -> dict[str, Any]:
        return {"status": "not_configured", "missing": missing, "raw_response_included": False}

    def _dry_run(self, *, endpoint: str, detail: str) -> dict[str, Any]:
        return {
            "status": "dry_run",
            "endpoint": endpoint,
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

    def _get_json_uncached(self, url: str, bearer: str) -> dict[str, Any]:
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

    def _http_fetch_refresh_secret(self) -> str | None:
        if not self.has_mail_password():
            return None
        url = f"{self.base_url}/token/auth_user"
        payload = {"mailaddress": self.email, "password": self.password}
        try:
            body = self._post_json_uncached(url, payload)
        except (urllib.error.HTTPError, OSError, ValueError):
            return None
        refresh = self._extract_refresh_secret(body)
        return str(refresh) if refresh else None

    def _http_fetch_id_secret_from_refresh(self, refresh: str) -> str | None:
        url = f"{self.base_url}/token/auth_refresh"
        payload = {"refreshtoken": refresh}
        try:
            body = self._post_json_uncached(url, payload)
        except (urllib.error.HTTPError, OSError, ValueError):
            return None
        id_tok = self._extract_id_secret(body)
        return str(id_tok) if id_tok else None

    # --- Safe public APIs (no token values returned) ---
    def get_refresh_token(self, *, attempt_live: bool = False) -> dict[str, Any]:
        if not self.is_enabled():
            return self._disabled(hint="JQUANTS_ENABLED=false")
        if not self.has_mail_password():
            return self._not_configured(missing=["JQUANTS_EMAIL", "JQUANTS_PASSWORD"])
        if not attempt_live:
            return self._dry_run(
                endpoint=f"{self.base_url}/token/auth_user",
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
        }

    def get_id_token(self, *, attempt_live: bool = False, refresh_override: str | None = None) -> dict[str, Any]:
        if not self.is_enabled():
            return self._disabled(hint="JQUANTS_ENABLED=false")

        refresh = refresh_override or self.refresh_token
        if not refresh:
            return self._not_configured(missing=["JQUANTS_REFRESH_TOKEN"])

        if not attempt_live:
            return self._dry_run(
                endpoint=f"{self.base_url}/token/auth_refresh",
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
        }

    def _resolve_bearer_secret_for_quotes_live(self) -> str | None:
        """Bearer for daily_quotes; never surfaced in CLI dict."""

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

        if not attempt_live:
            return self._dry_run(
                endpoint=f"{self.base_url}/prices/daily_quotes",
                detail=(
                    "Default is dry-run. Pass --live on debug jquants-daily-quotes AND "
                    "set JQUANTS_ALLOW_LIVE_HTTP=true to perform HTTP."
                ),
            )

        denial = self._live_gate_denied_reason(cli_live_requested=True)
        if denial:
            return self._live_blocked(reason=denial)

        if not self.is_configured():
            return self._not_configured(
                missing=["JQUANTS_ID_TOKEN", "JQUANTS_REFRESH_TOKEN", "(JQUANTS_EMAIL+PASSWORD)"],
            )

        bearer: str | None = self._resolve_bearer_secret_for_quotes_live()

        params: dict[str, str] = {"code": code}
        if date:
            params["date"] = date.replace("-", "")
        if from_date:
            params["from"] = from_date.replace("-", "")
        if to_date:
            params["to"] = to_date.replace("-", "")

        if not bearer:
            return {"status": "failed", "step": "resolve_bearer", "raw_response_included": False}

        query = urlencode(params)
        url = f"{self.base_url}/prices/daily_quotes?{query}"

        try:
            parsed = self._get_json_uncached(url, bearer)
        except urllib.error.HTTPError as e:
            return {
                "status": "http_error",
                "code": int(e.code),
                "detail": "***",
                "raw_response_included": False,
            }
        except OSError:
            return {"status": "error", "detail": "***", "raw_response_included": False}

        daily = parsed.get("daily_quotes")
        quotes = parsed.get("quotes") if isinstance(parsed.get("quotes"), list) else None
        rows = len(daily) if isinstance(daily, list) else (len(quotes) if quotes is not None else None)
        key = (
            "daily_quotes_row_count"
            if isinstance(daily, list)
            else ("quotes_row_count" if quotes is not None else "parsed_keys_count")
        )
        count_val = rows if rows is not None else len(parsed)

        return {
            "status": "success",
            "endpoint": "prices/daily_quotes",
            "code": code,
            key: count_val,
            "raw_response_included": False,
            "token_preview": "***",
        }


def jquants_client_from_env() -> JQuantsClient:
    return JQuantsClient.from_env()
