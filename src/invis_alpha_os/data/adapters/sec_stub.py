from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..market_data_adapter import MarketDataAdapter, QuoteSnapshot


class SecStubAdapter(MarketDataAdapter):
    name = "sec"
    mode = "metadata_stub"

    def health(self) -> dict[str, Any]:
        return {"adapter": self.name, "mode": self.mode, "status": "stub"}

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        return QuoteSnapshot(
            symbol=symbol,
            as_of=datetime.now(tz=timezone.utc),
            last_price=None,
            metadata={"source": "sec_stub", "note": "quote endpoint not provided"},
        )

    def get_company_metadata(self, symbol: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "source": "sec_stub",
            "status": "metadata_stub",
            "note": "Future SEC metadata integration target.",
        }

