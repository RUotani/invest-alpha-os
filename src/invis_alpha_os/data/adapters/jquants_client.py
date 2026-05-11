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
``to_date``). **Date values are sent as** ``YYYYMMDD`` **(Task 5.4, per official quick start)**. CLI may pass
``YYYY-MM-DD`` or ``YYYYMMDD``; invalid calendar dates → ``validation_error`` / ``invalid_date_format``. Base URLs that already end with ``/v2`` are
joined with paths like ``/equities/bars/daily`` so ``/v2/v2`` is not produced (Task 5.2). Use
``build_v2_daily_bars_request_preview`` / ``--preview-request`` to inspect URLs without HTTP or secrets.

**Task 5.3**: CLI accepts **code-only / date-only / code+date / code+range**; ``--date`` is mutually exclusive with
``--from-date``/``--to-date``; validation runs before HTTP and before ``--preview-request`` output.

**Task 5.4**: V2 wire dates are **YYYYMMDD** (official quick start); CLI accepts ``YYYY-MM-DD`` or ``YYYYMMDD``;
invalid calendar dates → ``invalid_date_format``.

**Task 5.5**: On HTTP errors, a short **masked** ``error_body_preview`` (no raw body, no ``x-api-key`` value).

**Task 5.6**: Optional env **``JQUANTS_DATA_AVAILABLE_FROM``** / **``TO``** — when both parse, V2 CLI rejects
``--date`` / ``--from-date`` / ``--to-date`` outside that inclusive window before HTTP (``validation_error`` /
``date_out_of_available_range``).

**Task 6**: **``debug jquants-watchlist-bars``** reads ``jp_watchlist`` tickers; only **4-digit** codes are sent to V2 daily bars (see ``config/jp_watchlist.py``).

**Task 7**: Daily report includes a **dry-run / status-only** **J-Quants Watchlist Bars Check** section (no HTTP, no API keys). See ``reports/jquants_watchlist_daily.py``.

**Task 8**: Same section adds **readiness (Green / Yellow / Red)** from config + env + watchlist counts only (still **no HTTP**).

``debug jquants-status`` must never perform HTTP — use ``safe_auth_status()`` only.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date as _date
from typing import Any, Sequence
from urllib.parse import urlencode

# V2 daily bars: scan in this order; first present key must map to a list (Task 5).
_V2_DAILY_QUOTES_BODY_KEYS: tuple[str, ...] = ("data", "daily_quotes", "bars", "results")


def _parse_v2_daily_bars_date(value: str) -> str | None:
    """Parse a human or compact date into **YYYYMMDD** for V2 wire query, or ``None`` if invalid.

    Accepted:

    - ``YYYYMMDD`` (8 digits), calendar-valid;
    - ``YYYY-MM-DD`` with zero-padded month and day, calendar-valid.

    Other shapes (e.g. ``2026-5-8``) are rejected.
    """

    s = (value or "").strip()
    if not s:
        return None

    m_iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m_iso:
        y, mo, day = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        try:
            _date(y, mo, day)
        except ValueError:
            return None
        return f"{y:04d}{mo:02d}{day:02d}"

    m_compact = re.fullmatch(r"(\d{8})", s)
    if not m_compact:
        return None
    y, mo, day = int(s[0:4]), int(s[4:6]), int(s[6:8])
    try:
        _date(y, mo, day)
    except ValueError:
        return None
    return s


def _strip_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _daily_quotes_cli_validation_error(reason: str) -> dict[str, Any]:
    return {"status": "validation_error", "reason": reason, "raw_response_included": False}


def _yyyymmdd_to_calendar_date(wd: str) -> _date:
    return _date(int(wd[0:4]), int(wd[4:6]), int(wd[6:8]))


def jquants_data_availability_bounds_from_env() -> tuple[_date | None, _date | None]:
    """Inclusive subscription window from env, or ``(None, None)`` if guard should be off."""

    raw_a = (os.getenv("JQUANTS_DATA_AVAILABLE_FROM") or "").strip() or None
    raw_b = (os.getenv("JQUANTS_DATA_AVAILABLE_TO") or "").strip() or None
    if not raw_a or not raw_b:
        return (None, None)
    wa = _parse_v2_daily_bars_date(raw_a)
    wb = _parse_v2_daily_bars_date(raw_b)
    if wa is None or wb is None:
        return (None, None)
    da = _yyyymmdd_to_calendar_date(wa)
    db = _yyyymmdd_to_calendar_date(wb)
    if da > db:
        return (None, None)
    return (da, db)


def _daily_quotes_date_out_of_available_range_error(lo: _date, hi: _date) -> dict[str, Any]:
    return {
        "status": "validation_error",
        "reason": "date_out_of_available_range",
        "raw_response_included": False,
        "data_available_from": lo.isoformat(),
        "data_available_to": hi.isoformat(),
    }


def _validate_v2_dates_within_data_availability(
    d: str | None, fd: str | None, td: str | None
) -> dict[str, Any] | None:
    """Reject wire dates outside ``JQUANTS_DATA_AVAILABLE_*`` when both env vars define an inclusive window."""

    lo, hi = jquants_data_availability_bounds_from_env()
    if lo is None or hi is None:
        return None
    if d is None and fd is None and td is None:
        return None

    for raw in (d, fd, td):
        if raw is None:
            continue
        wd = _parse_v2_daily_bars_date(raw)
        assert wd is not None
        dt = _yyyymmdd_to_calendar_date(wd)
        if dt < lo or dt > hi:
            return _daily_quotes_date_out_of_available_range_error(lo, hi)
    return None


def _validate_quote_date_fields_parseable(
    d: str | None, fd: str | None, td: str | None
) -> dict[str, Any] | None:
    """Require each non-empty date field to parse to a calendar-valid ``YYYYMMDD``."""

    for raw in (d, fd, td):
        if raw is None:
            continue
        if _parse_v2_daily_bars_date(raw) is None:
            return _daily_quotes_cli_validation_error("invalid_date_format")
    return None


def _read_http_error_body_bytes(exc: urllib.error.HTTPError) -> bytes:
    try:
        raw = exc.read()
    except Exception:
        return b""
    if not raw:
        return b""
    if isinstance(raw, str):
        return raw.encode("utf-8", errors="replace")
    return bytes(raw)


def _normalize_error_preview_ws(text: str) -> str:
    t = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return " ".join(t.split())


def _truncate_error_preview(text: str, max_len: int = 300) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len]


_JSON_ERR_BODY_KEYS_TO_MASK = (
    "refresh_token",
    "access_token",
    "refreshToken",
    "accessToken",
    "id_token",
    "idToken",
    "authorization",
    "x-api-key",
    "password",
    "api_key",
    "apikey",
    "apiKey",
    "token",
    "secret",
    "client_secret",
    "clientSecret",
    "session",
    "cookie",
)
_JSON_ERR_BODY_KEY_ALT = "|".join(re.escape(k) for k in sorted(set(_JSON_ERR_BODY_KEYS_TO_MASK), key=len, reverse=True))
_JSON_ERR_KEY_QUOTED_RE = re.compile(
    rf'(?i)("(?:{_JSON_ERR_BODY_KEY_ALT})"\s*:\s*")([^"]*)(")'
)


def _mask_sensitive_preview(text: str, secrets: Sequence[str]) -> str:
    """Mask env/client secrets and common bearer/header patterns (never emit x-api-key values)."""

    out = text
    ordered = sorted((s for s in secrets if s and len(s) > 0), key=len, reverse=True)
    seen: set[str] = set()
    for s in ordered:
        if s in seen:
            continue
        seen.add(s)
        # Avoid turning every "k" in unrelated text into "***" when env holds a 1-char test key.
        if len(s) >= 4:
            out = out.replace(s, "***")
    for s in ordered:
        if len(s) < 4:
            continue
        try:
            out = re.sub(re.escape(s), "***", out, flags=re.IGNORECASE)
        except re.error:
            pass
    out = re.sub(r"(?i)\bBearer\s+\S+", "Bearer ***", out)
    out = _JSON_ERR_KEY_QUOTED_RE.sub(r"\1***\3", out)
    out = re.sub(
        r"(?i)\b(x-api-key|authorization|password|token|access_token|refresh_token|id_token|"
        r"api_key|apikey|secret|client_secret|session|cookie)\s*:\s*\S+",
        r"\1: ***",
        out,
    )
    return out


def _json_http_error_extract_fields(obj: dict[str, Any], secrets: Sequence[str]) -> str | None:
    """Prefer ``message`` / ``error`` / ``detail`` / ``title`` / ``type`` for a short string."""

    order = ("message", "error", "detail", "title", "type")
    parts: list[str] = []
    for k in order:
        if k not in obj:
            continue
        v = obj[k]
        if isinstance(v, bool):
            parts.append(f"{k}: {v}")
        elif isinstance(v, str) and v.strip():
            parts.append(f"{k}: {_mask_sensitive_preview(v, secrets)}")
        elif isinstance(v, (int, float)):
            parts.append(f"{k}: {v}")
        elif v is None:
            continue
        else:
            try:
                compact = json.dumps(v, ensure_ascii=False)
            except (TypeError, ValueError):
                compact = str(v)
            compact = _mask_sensitive_preview(compact, secrets)
            if len(compact) > 160:
                compact = compact[:157] + "..."
            parts.append(f"{k}: {compact}")
    if parts:
        return "; ".join(parts)
    return None


def summarize_http_error_body_preview(raw: bytes, secrets: Sequence[str]) -> str | None:
    """Build a short, masked preview of an HTTP error body (never the full raw response)."""

    if not raw:
        return None
    try:
        decoded = raw.decode("utf-8", errors="replace")
    except Exception:
        return None
    stripped = decoded.strip()
    if not stripped:
        return None

    extracted: str | None = None
    json_ok = False
    json_is_object = False
    try:
        parsed: Any = json.loads(stripped)
        json_ok = True
        if isinstance(parsed, dict):
            json_is_object = True
            extracted = _json_http_error_extract_fields(parsed, list(secrets))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    if json_ok:
        if json_is_object:
            if extracted is None:
                return None
            preview = extracted
        else:
            return None
    else:
        preview = stripped

    preview = _normalize_error_preview_ws(preview)
    preview = _mask_sensitive_preview(preview, list(secrets))
    preview = _truncate_error_preview(preview, 300)
    return preview if preview else None


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

    def _secret_strings_for_error_preview(self) -> list[str]:
        """Strings that must never appear verbatim in ``error_body_preview``."""

        out: list[str] = []
        env_k = _blank_to_none(os.getenv("JQUANTS_API_KEY"))
        if env_k:
            out.append(env_k)
        if self.api_key and self.api_key not in out:
            out.append(self.api_key)
        if self.id_token and self.id_token not in out:
            out.append(self.id_token)
        if self.refresh_token and self.refresh_token not in out:
            out.append(self.refresh_token)
        if self.password and self.password not in out:
            out.append(self.password)
        return out

    def _http_error_body_preview_from_exc(self, exc: urllib.error.HTTPError) -> str | None:
        raw = _read_http_error_body_bytes(exc)
        return summarize_http_error_body_preview(raw, self._secret_strings_for_error_preview())

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
        code: str | None,
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
        code: str | None,
        *,
        date: str | None,
        from_date: str | None,
        to_date: str | None,
    ) -> dict[str, str]:
        params: dict[str, str] = {}
        c = _strip_optional_str(code)
        if c is not None:
            params["code"] = c
        if date:
            wd = _parse_v2_daily_bars_date(date)
            assert wd is not None
            params["date"] = wd
        if from_date:
            wf = _parse_v2_daily_bars_date(from_date)
            assert wf is not None
            params["from"] = wf
        if to_date:
            wt = _parse_v2_daily_bars_date(to_date)
            assert wt is not None
            params["to"] = wt
        return params

    def _v2_daily_bars_endpoint_without_query(self) -> str | None:
        if not self.base_url:
            return None
        path = self._paths.get("daily_quotes")
        if path is None:
            return None
        return _join_v2_base_and_path(self.base_url, path)

    def validate_daily_quotes_cli_args(
        self,
        code: str | None,
        *,
        date: str | None,
        from_date: str | None,
        to_date: str | None,
    ) -> dict[str, Any] | None:
        """CLI / query validation for daily bars (before HTTP).

        V2 allows ``code`` only, ``date`` only, ``code``+``date``, ``code``+``from``/``to``. ``date`` cannot
        combine with ``from``/``to``. At least one of ``code``, ``date``, ``from``, ``to`` must be set.
        V1 requires ``--code`` (legacy bearer path).
        """

        if self.api_version_effective is None:
            return None

        c = _strip_optional_str(code)
        d = _strip_optional_str(date)
        fd = _strip_optional_str(from_date)
        td = _strip_optional_str(to_date)

        if self.api_version_effective == "v1":
            if c is None:
                return _daily_quotes_cli_validation_error("v1_requires_code")
            if d is not None and (fd is not None or td is not None):
                return _daily_quotes_cli_validation_error("date_mutually_exclusive_with_from_to")
            bad_dates = _validate_quote_date_fields_parseable(d, fd, td)
            if bad_dates is not None:
                return bad_dates
            return None

        assert self.api_version_effective == "v2"
        if c is None and d is None and fd is None and td is None:
            return _daily_quotes_cli_validation_error("missing_all_of_code_date_from_to")
        if d is not None and (fd is not None or td is not None):
            return _daily_quotes_cli_validation_error("date_mutually_exclusive_with_from_to")
        bad_dates = _validate_quote_date_fields_parseable(d, fd, td)
        if bad_dates is not None:
            return bad_dates
        out_range = _validate_v2_dates_within_data_availability(d, fd, td)
        if out_range is not None:
            return out_range
        return None

    def build_v2_daily_bars_request_preview(
        self,
        code: str | None = None,
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

        c = _strip_optional_str(code)
        d = _strip_optional_str(date)
        fd = _strip_optional_str(from_date)
        td = _strip_optional_str(to_date)

        verr = self.validate_daily_quotes_cli_args(c, date=d, from_date=fd, to_date=td)
        if verr is not None:
            return {**verr, **meta}

        if not self.has_base_url():
            return self._missing_base_url_reply() | meta

        endpoint_wo_q = self._v2_daily_bars_endpoint_without_query()
        if endpoint_wo_q is None:
            return self._missing_base_url_reply() | meta

        q_params = self._v2_daily_bars_query_params(c, date=d, from_date=fd, to_date=td)
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
        code: str | None = None,
        *,
        date: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        attempt_live: bool = False,
    ) -> dict[str, Any]:
        bad_ver = self._maybe_unsupported_api_version()
        if bad_ver is not None:
            return bad_ver

        code = _strip_optional_str(code)
        date = _strip_optional_str(date)
        from_date = _strip_optional_str(from_date)
        to_date = _strip_optional_str(to_date)

        verr = self.validate_daily_quotes_cli_args(code, date=date, from_date=from_date, to_date=to_date)
        if verr is not None:
            return verr

        if not self.is_enabled():
            return self._disabled(hint="JQUANTS_ENABLED=false")

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
                    "error_body_preview": self._http_error_body_preview_from_exc(e),
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
            wd = _parse_v2_daily_bars_date(date)
            assert wd is not None
            params["date"] = wd
        if from_date:
            wf = _parse_v2_daily_bars_date(from_date)
            assert wf is not None
            params["from"] = wf
        if to_date:
            wt = _parse_v2_daily_bars_date(to_date)
            assert wt is not None
            params["to"] = wt

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
                "error_body_preview": self._http_error_body_preview_from_exc(e),
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
