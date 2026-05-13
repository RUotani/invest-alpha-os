"""Observation-only US equities / ETFs / proxies from ``us_watchlist.yaml`` (Main R design skeleton)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.data.cache_wire_slug import sanitize_provider_wire_slug_for_cache_filename


def normalize_us_symbol(raw: str) -> str | None:
    """Normalize a US-style symbol label for cache filenames and reports.

    - Strip; uppercase ASCII letters.
    - Allow ``[A-Z0-9._-]+`` constrained to slug rules (starts/ends alphanumeric, max length).
    - Rejects empty, separators, traversal, control characters.

    Examples: ``"msft"`` → ``MSFT``, ``"brk.b"`` → ``BRK.B``, ``GOOGL`` → ``GOOGL``.
    """

    if "/" in raw or "\\" in (raw or ""):
        return None
    s = (raw or "").strip().upper()
    if not s:
        return None
    if ".." in s:
        return None
    if any(ord(ch) < 32 for ch in s):
        return None
    try:
        return sanitize_provider_wire_slug_for_cache_filename(s)
    except ValueError:
        return None


def _flatten_section(rows: object) -> list[str]:
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            t = str(row.get("ticker", "") or row.get("symbol", "")).strip()
            if t:
                out.append(t)
        elif isinstance(row, str) and row.strip():
            out.append(row.strip())
    return out


def extract_us_watchlist_symbols(data: dict[str, Any]) -> list[str]:
    """Flatten ``us_equities``, ``us_etfs``, ``crypto_proxy`` in declared order."""

    parts: list[str] = []
    for key in ("us_equities", "us_etfs", "crypto_proxy"):
        rows = data.get(key)
        parts.extend(_flatten_section(rows))
    return parts


def load_us_watchlist_tickers(path: Path | None = None) -> list[str]:
    """Load YAML, normalize symbols, preserve order with first-wins deduplication."""

    p = (CONFIG_DIR / "us_watchlist.yaml") if path is None else Path(path)
    payload = load_yaml(p)
    seen: set[str] = set()
    out: list[str] = []
    for raw in extract_us_watchlist_symbols(payload):
        n = normalize_us_symbol(str(raw))
        if n is None or n in seen:
            continue
        seen.add(n)
        out.append(n)
    return out


def us_symbol_asset_class_defaults(data: dict[str, Any]) -> dict[str, str]:
    """Map normalized symbol → ``us_equity`` | ``us_etf`` | ``crypto_proxy`` from YAML grouping."""

    m: dict[str, str] = {}
    buckets: tuple[tuple[str, str], ...] = (
        ("us_equities", "us_equity"),
        ("us_etfs", "us_etf"),
        ("crypto_proxy", "crypto_proxy"),
    )
    for yaml_key, asset in buckets:
        for raw in _flatten_section(data.get(yaml_key)):
            n = normalize_us_symbol(raw)
            if n is None:
                continue
            m.setdefault(n, asset)
    return m
