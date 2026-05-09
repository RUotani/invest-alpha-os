from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    as_of: datetime
    last_price: float | None
    currency: str | None = None
    metadata: dict[str, Any] | None = None


class MarketDataAdapter(ABC):
    """Abstract interface for future high-quality market data providers."""

    name: str = "abstract"
    mode: str = "prototype"

    @abstractmethod
    def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, symbol: str) -> QuoteSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_company_metadata(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

