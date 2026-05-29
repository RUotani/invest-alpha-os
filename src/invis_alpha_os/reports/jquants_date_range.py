"""J-Quants contract date range parsing and refresh clamp helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache

_DATE_ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DATE_COMPACT_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
DEFAULT_LOOKBACK_DAYS = 400


def parse_contract_date(value: str | None) -> date | None:
    raw = (value or "").strip()
    if not raw:
        return None
    match_iso = _DATE_ISO_RE.fullmatch(raw)
    if match_iso:
        try:
            return date(int(match_iso.group(1)), int(match_iso.group(2)), int(match_iso.group(3)))
        except ValueError:
            return None
    match_compact = _DATE_COMPACT_RE.fullmatch(raw)
    if match_compact:
        try:
            return date(int(match_compact.group(1)), int(match_compact.group(2)), int(match_compact.group(3)))
        except ValueError:
            return None
    return None


def contract_dates_from_env(env: dict[str, str]) -> dict[str, Any]:
    raw_from = str(env.get("JQUANTS_DATA_AVAILABLE_FROM", "")).strip()
    raw_to = str(env.get("JQUANTS_DATA_AVAILABLE_TO", "")).strip()
    parsed_from = parse_contract_date(raw_from) if raw_from else None
    parsed_to = parse_contract_date(raw_to) if raw_to else None
    return {
        "data_available_from_present": bool(raw_from),
        "data_available_to_present": bool(raw_to),
        "data_available_from": parsed_from.isoformat() if parsed_from else None,
        "data_available_to": parsed_to.isoformat() if parsed_to else None,
        "data_available_date_redacted": False,
    }


def compute_requested_refresh_range(
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    requested_to: date | None = None,
) -> tuple[str, str]:
    to_d = requested_to or date.today()
    from_d = to_d - timedelta(days=lookback_days)
    return from_d.isoformat(), to_d.isoformat()


def is_effective_refresh_range(clamped_to_date: str, latest_bar_date: str | None) -> bool:
    if not latest_bar_date:
        return True
    try:
        return date.fromisoformat(clamped_to_date) > date.fromisoformat(latest_bar_date)
    except ValueError:
        return True


def latest_bar_dates_for_targets(targets: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for ticker in targets:
        loaded = load_jquants_daily_bars_cache(ticker)
        if not loaded:
            out[ticker] = None
            continue
        bars, _meta = loaded
        out[ticker] = str(bars[-1]["date"]).strip() if bars else None
    return out


@dataclass(frozen=True)
class DateRangeResolution:
    requested_from_date: str
    requested_to_date: str
    clamped_from_date: str
    clamped_to_date: str
    date_range_clamped: bool
    requested_to_date_within_contract: bool
    date_range_clamp_required: bool
    date_range_validated_before_http: bool
    http_prevented_by_date_validation: bool
    validation_status: str
    validation_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested_from_date": self.requested_from_date,
            "requested_to_date": self.requested_to_date,
            "clamped_from_date": self.clamped_from_date,
            "clamped_to_date": self.clamped_to_date,
            "date_range_clamped": self.date_range_clamped,
            "requested_to_date_within_contract": self.requested_to_date_within_contract,
            "date_range_clamp_required": self.date_range_clamp_required,
            "date_range_validated_before_http": self.date_range_validated_before_http,
            "http_prevented_by_date_validation": self.http_prevented_by_date_validation,
            "validation_status": self.validation_status,
            "validation_reason": self.validation_reason,
        }


def resolve_refresh_date_range(
    env: dict[str, str],
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    requested_to: date | None = None,
    allow_date_clamp: bool = False,
    latest_bar_dates: dict[str, str | None] | None = None,
    check_effective_range: bool = False,
) -> DateRangeResolution:
    req_from, req_to = compute_requested_refresh_range(lookback_days=lookback_days, requested_to=requested_to)
    contract = contract_dates_from_env(env)
    parsed_to = parse_contract_date(contract.get("data_available_to"))
    parsed_from = parse_contract_date(contract.get("data_available_from"))
    req_to_d = date.fromisoformat(req_to)
    req_from_d = date.fromisoformat(req_from)

    within_contract = parsed_to is None or req_to_d <= parsed_to
    clamp_required = parsed_to is not None and req_to_d > parsed_to

    if clamp_required and not allow_date_clamp:
        return DateRangeResolution(
            requested_from_date=req_from,
            requested_to_date=req_to,
            clamped_from_date=req_from,
            clamped_to_date=req_to,
            date_range_clamped=False,
            requested_to_date_within_contract=False,
            date_range_clamp_required=True,
            date_range_validated_before_http=True,
            http_prevented_by_date_validation=True,
            validation_status="date_range_out_of_contract",
            validation_reason="requested_to_date exceeds contract data_available_to",
        )

    clamped_to_d = min(req_to_d, parsed_to) if parsed_to else req_to_d
    clamped_from_d = req_from_d
    if parsed_from and clamped_from_d < parsed_from:
        clamped_from_d = parsed_from
    if parsed_to and clamped_from_d > parsed_to:
        clamped_from_d = parsed_to

    clamped_from = clamped_from_d.isoformat()
    clamped_to = clamped_to_d.isoformat()
    date_clamped = clamped_to != req_to or clamped_from != req_from

    if check_effective_range and latest_bar_dates:
        if all(not is_effective_refresh_range(clamped_to, lbd) for lbd in latest_bar_dates.values()):
            return DateRangeResolution(
                requested_from_date=req_from,
                requested_to_date=req_to,
                clamped_from_date=clamped_from,
                clamped_to_date=clamped_to,
                date_range_clamped=date_clamped,
                requested_to_date_within_contract=within_contract or allow_date_clamp,
                date_range_clamp_required=clamp_required,
                date_range_validated_before_http=True,
                http_prevented_by_date_validation=True,
                validation_status="no_effective_refresh_range",
                validation_reason="clamped_to_date is not newer than cached latest_bar_date for all targets",
            )

    return DateRangeResolution(
        requested_from_date=req_from,
        requested_to_date=req_to,
        clamped_from_date=clamped_from,
        clamped_to_date=clamped_to,
        date_range_clamped=date_clamped,
        requested_to_date_within_contract=within_contract or (clamp_required and allow_date_clamp),
        date_range_clamp_required=clamp_required,
        date_range_validated_before_http=True,
        http_prevented_by_date_validation=False,
        validation_status="ok",
    )
