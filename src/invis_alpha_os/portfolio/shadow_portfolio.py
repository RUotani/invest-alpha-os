from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from invis_alpha_os.core.jsonl_store import JsonlStore
from invis_alpha_os.core.models import ShadowPosition
from invis_alpha_os.core.serialization import parse_date, parse_datetime


@dataclass(frozen=True)
class ShadowPortfolioService:
    path: Path

    def _store(self) -> JsonlStore[ShadowPosition]:
        return JsonlStore(
            path=self.path,
            encode=lambda x: {
                "id": x.id,
                "created_at": x.created_at,
                "symbol": x.symbol,
                "quantity": x.quantity,
                "entry_price": x.entry_price,
                "entry_date": x.entry_date,
                "thesis_evidence_ids": x.thesis_evidence_ids,
                "tags": x.tags,
                "extra": x.extra,
            },
            decode=lambda d: ShadowPosition(
                id=d["id"],
                created_at=parse_datetime(d.get("created_at")) or ShadowPosition().created_at,
                symbol=d.get("symbol", ""),
                quantity=float(d.get("quantity", 0.0)),
                entry_price=d.get("entry_price"),
                entry_date=parse_date(d.get("entry_date")),
                thesis_evidence_ids=list(d.get("thesis_evidence_ids", [])),
                tags=list(d.get("tags", [])),
                extra=dict(d.get("extra", {})),
            ),
        )

    def list_positions(self) -> list[ShadowPosition]:
        return list(self._store().iter_all())

