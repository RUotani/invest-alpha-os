"""Ticker display names for compact reports (config-only; no network)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR

_JP_CODE_RE = re.compile(r"^[0-9A-Za-z]{4}$")


@lru_cache(maxsize=1)
def _display_name_maps() -> tuple[dict[str, str], dict[str, str]]:
    path = CONFIG_DIR / "symbol_display_names.yaml"
    if not path.is_file():
        return {}, {}
    data = load_yaml(path)
    jp_raw = data.get("jp") if isinstance(data, dict) else {}
    us_raw = data.get("us") if isinstance(data, dict) else {}
    jp: dict[str, str] = {}
    us: dict[str, str] = {}
    if isinstance(jp_raw, dict):
        for k, v in jp_raw.items():
            if v:
                jp[str(k).strip().upper()] = str(v).strip()
    if isinstance(us_raw, dict):
        for k, v in us_raw.items():
            if v:
                us[str(k).strip().upper()] = str(v).strip()
    return jp, us


def _normalize_code(code: str) -> str:
    return str(code or "").strip().upper()


def infer_market(code: str) -> str:
    c = _normalize_code(code)
    if _JP_CODE_RE.fullmatch(c):
        return "jp"
    return "us"


def display_name(code: str, *, market: str | None = None) -> str:
    """Short name for symbol, or raw code if unknown."""

    c = _normalize_code(code)
    if not c:
        return ""
    m = (market or infer_market(c)).strip().lower()
    jp_map, us_map = _display_name_maps()
    if m == "jp":
        return jp_map.get(c, c)
    if m == "us":
        return us_map.get(c, c)
    return jp_map.get(c) or us_map.get(c) or c


def display_symbol(code: str, *, market: str | None = None) -> str:
    """Compact ``CODE Name`` for tables; keeps raw code when name unknown."""

    c = _normalize_code(code)
    if not c:
        return ""
    name = display_name(c, market=market)
    if name == c:
        return c
    return f"{c} {name}"


def format_us_preview_symbol_cell(symbol: str) -> str:
    return display_symbol(symbol, market="us")
