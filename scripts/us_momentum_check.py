#!/usr/bin/env python3
"""Verify US momentum cache-only Markdown after local fixture import (no HTTP).

Invoked via: ``PYTHON=.venv/bin/python make us-momentum-check``
"""

from __future__ import annotations

import urllib.request

from invis_alpha_os.reports.momentum_daily import render_us_momentum_cache_only_section


def main() -> None:
    sentinel = urllib.request.urlopen

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("us-momentum-check must not use live HTTP")

    urllib.request.urlopen = _boom  # type: ignore[method-assign]

    try:
        text = render_us_momentum_cache_only_section()
    finally:
        urllib.request.urlopen = sentinel  # type: ignore[method-assign]

    need = (
        "## Momentum Signals — US Cache Only",
        "**Bars source:** `cache` — **US**",
        "**No live data fetch**",
        "| MSFT |",
        "| GOOGL |",
        "| GLDM |",
    )
    missing = [s for s in need if s not in text]
    if missing:
        raise SystemExit(f"us-momentum-check failed; missing: {missing!r}\n\n---\n{text}\n---")

    low = text.lower()
    for tok in ("raw_response", "api_key", "authorization:", "bearer "):
        if tok in low:
            raise SystemExit(f"us-momentum-check: forbidden token in output: {tok!r}")


if __name__ == "__main__":
    main()
