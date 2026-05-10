"""Global fallback prototype; JP primary candidate is J-Quants (see jquants_stub)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..market_data_adapter import MarketDataAdapter, QuoteSnapshot


class YFinanceFallbackAdapter(MarketDataAdapter):
    name = "yfinance"
    mode = "fallback_prototype"

    def health(self) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "mode": self.mode,
            "status": "available_as_fallback",
            "note": "Phase 0 uses this adapter as prototype only.",
        }

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        # Phase 0: no real API call; keep deterministic stub behavior.
        return QuoteSnapshot(
            symbol=symbol,
            as_of=datetime.now(tz=timezone.utc),
            last_price=None,
            currency=None,
            metadata={"source": "yfinance_stub", "phase": "0-v1.1"},
        )

    def get_company_metadata(self, symbol: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "source": "yfinance_stub",
            "status": "not_implemented",
            "note": "Reserved for future metadata enrichment.",
        }

