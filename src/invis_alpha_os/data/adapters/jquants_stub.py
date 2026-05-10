"""J-Quants API placeholder: Phase 1a Task 1 has no HTTP calls or secrets."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from ..market_data_adapter import MarketDataAdapter, QuoteSnapshot


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class JQuantsStubAdapter(MarketDataAdapter):
    """J-Quants integration placeholder: no HTTP, no secrets required for CI."""

    name = "jquants"
    mode = "stub"

    def is_enabled(self) -> bool:
        return _truthy_env("JQUANTS_ENABLED", default="false")

    def health(self) -> dict[str, Any]:
        if not self.is_enabled():
            return {
                "adapter": self.name,
                "mode": self.mode,
                "enabled": False,
                "status": "disabled_not_configured",
                "note": "Set JQUANTS_ENABLED=true for stub-only exploration; no HTTP in Phase 1a Task 1.",
            }
        return {
            "adapter": self.name,
            "mode": self.mode,
            "enabled": True,
            "status": "stub_no_http",
            "note": "Phase 1a: enabled flag set but live API calls are still not implemented.",
        }

    def get_quote(self, symbol: str) -> QuoteSnapshot:
        return QuoteSnapshot(
            symbol=symbol,
            as_of=datetime.now(tz=timezone.utc),
            last_price=None,
            currency="JPY",
            metadata={
                "source": "jquants_stub",
                "enabled": self.is_enabled(),
            },
        )

    def get_company_metadata(self, symbol: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "source": "jquants_stub",
            "listed_info": "not_requested",
            "enabled": self.is_enabled(),
        }

    def get_daily_quotes_stub(self, symbol: str = "7011") -> dict[str, Any]:
        """Returns placeholder daily quotes payload (no API)."""

        if not self.is_enabled():
            return {"status": "disabled", "symbol": symbol, "rows": []}

        return {
            "status": "stub",
            "symbol": symbol,
            "rows": [],
            "note": "Replace with prices/daily_quotes mapping in a future task.",
        }

    def get_listed_info_stub(self, symbol: str = "7011") -> dict[str, Any]:
        """Returns placeholder listed/info payload (no API)."""

        if not self.is_enabled():
            return {"status": "disabled", "symbol": symbol, "items": []}

        return {
            "status": "stub",
            "symbol": symbol,
            "items": [],
            "note": "Replace with listed/info mapping in a future task.",
        }
