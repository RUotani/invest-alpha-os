"""J-Quants contract env presence diagnostics for context/readiness outputs."""

from __future__ import annotations

import os
from typing import Any

from invis_alpha_os.reports.jquants_date_range import contract_dates_from_env

_JP_MARKETS = frozenset({"JP"})
_STALE_FRESHNESS = frozenset({"stale", "data_update_required", "cache_missing", "partial_history"})


def jquants_contract_env_loaded(env: dict[str, str] | None = None) -> bool:
    env_map = env if env is not None else dict(os.environ)
    contract = contract_dates_from_env(env_map)
    return bool(contract.get("data_available_to_present"))


def build_contract_env_status(env: dict[str, str] | None = None) -> dict[str, Any]:
    env_map = env if env is not None else dict(os.environ)
    contract = contract_dates_from_env(env_map)
    loaded = bool(contract.get("data_available_to_present"))
    return {
        "jquants_contract_env_loaded": loaded,
        "contract_env_not_loaded": not loaded,
        "data_available_to_present": contract.get("data_available_to_present"),
        "data_available_from_present": contract.get("data_available_from_present"),
        "contract_env_hint": (
            None
            if loaded
            else "Pass --env-file with JQUANTS_DATA_AVAILABLE_TO for data_contract_limited classification"
        ),
    }


def jp_stale_candidates_without_contract_env(
    candidates: list[dict[str, Any]],
    *,
    env: dict[str, str] | None = None,
) -> list[str]:
    if jquants_contract_env_loaded(env):
        return []
    tickers: list[str] = []
    for row in candidates:
        if not isinstance(row, dict):
            continue
        market = str(row.get("market", "")).strip().upper()
        freshness = str(row.get("freshness_classification", "")).strip()
        ticker = str(row.get("ticker", "")).strip()
        if market in _JP_MARKETS and freshness in _STALE_FRESHNESS and ticker:
            tickers.append(ticker)
    return tickers


def append_contract_env_warning(
    timing_warnings: list[str] | None,
    *,
    env: dict[str, str] | None = None,
    market: str,
    freshness_classification: str,
) -> list[str]:
    out = list(timing_warnings or [])
    norm_market = market.strip().upper()
    if (
        not jquants_contract_env_loaded(env)
        and norm_market in _JP_MARKETS
        and freshness_classification in _STALE_FRESHNESS
        and "contract_env_not_loaded" not in out
    ):
        out.append("contract_env_not_loaded")
    return out
