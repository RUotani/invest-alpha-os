from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from .jsonl_store import JsonlStore
from .models import DataConfidence, Evidence
from .serialization import parse_datetime


class EvidenceStore(Protocol):
    def add(self, evidence: Evidence) -> None: ...
    def iter_all(self) -> Iterable[Evidence]: ...


@dataclass(frozen=True)
class LocalFileEvidenceStore(EvidenceStore):
    store: JsonlStore[Evidence]

    @staticmethod
    def default(path: Path) -> "LocalFileEvidenceStore":
        def encode(e: Evidence) -> dict:
            return {
                "id": e.id,
                "created_at": e.created_at,
                "source": e.source,
                "data_confidence": e.data_confidence.value,
                "symbol": e.symbol,
                "title": e.title,
                "note": e.note,
                "external_url": e.external_url,
                "tags": e.tags,
                "extra": e.extra,
            }

        def decode(d: dict) -> Evidence:
            return Evidence(
                id=d["id"],
                created_at=parse_datetime(d.get("created_at")) or Evidence().created_at,
                source=d.get("source", "manual"),
                data_confidence=DataConfidence(d.get("data_confidence", DataConfidence.mid.value)),
                symbol=d.get("symbol"),
                title=d.get("title"),
                note=d.get("note"),
                external_url=d.get("external_url"),
                tags=list(d.get("tags", [])),
                extra=dict(d.get("extra", {})),
            )

        return LocalFileEvidenceStore(store=JsonlStore(path=path, encode=encode, decode=decode))

    def add(self, evidence: Evidence) -> None:
        self.store.append(evidence)

    def iter_all(self) -> Iterable[Evidence]:
        return self.store.iter_all()

