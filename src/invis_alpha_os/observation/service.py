from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from invis_alpha_os.core.jsonl_store import JsonlStore
from invis_alpha_os.core.models import ObservationLogEntry, OutcomeRecord
from invis_alpha_os.core.serialization import parse_date, parse_datetime


@dataclass(frozen=True)
class ObservationService:
    observation_path: Path
    outcome_path: Path

    def _observation_store(self) -> JsonlStore[ObservationLogEntry]:
        return JsonlStore(
            path=self.observation_path,
            encode=lambda x: {
                "id": x.id,
                "created_at": x.created_at,
                "symbol": x.symbol,
                "note": x.note,
                "evidence_ids": x.evidence_ids,
                "tags": x.tags,
            },
            decode=lambda d: ObservationLogEntry(
                id=d["id"],
                created_at=parse_datetime(d.get("created_at")) or ObservationLogEntry().created_at,
                symbol=d.get("symbol"),
                note=d.get("note", ""),
                evidence_ids=list(d.get("evidence_ids", [])),
                tags=list(d.get("tags", [])),
            ),
        )

    def _outcome_store(self) -> JsonlStore[OutcomeRecord]:
        return JsonlStore(
            path=self.outcome_path,
            encode=lambda x: {
                "id": x.id,
                "created_at": x.created_at,
                "symbol": x.symbol,
                "decision_date": x.decision_date,
                "outcome_date": x.outcome_date,
                "result": x.result,
                "note": x.note,
                "related_observation_id": x.related_observation_id,
                "related_shadow_position_id": x.related_shadow_position_id,
                "evidence_ids": x.evidence_ids,
                "extra": x.extra,
            },
            decode=lambda d: OutcomeRecord(
                id=d["id"],
                created_at=parse_datetime(d.get("created_at")) or OutcomeRecord().created_at,
                symbol=d.get("symbol", ""),
                decision_date=parse_date(d.get("decision_date")),
                outcome_date=parse_date(d.get("outcome_date")),
                result=d.get("result", "unknown"),
                note=d.get("note"),
                related_observation_id=d.get("related_observation_id"),
                related_shadow_position_id=d.get("related_shadow_position_id"),
                evidence_ids=list(d.get("evidence_ids", [])),
                extra=dict(d.get("extra", {})),
            ),
        )

    def log_observation(self, symbol: str | None, note: str) -> ObservationLogEntry:
        row = ObservationLogEntry(symbol=symbol, note=note)
        self._observation_store().append(row)
        return row

    def log_outcome(
        self,
        symbol: str,
        result: str,
        note: str | None = None,
        decision_date: date | None = None,
        outcome_date: date | None = None,
    ) -> OutcomeRecord:
        row = OutcomeRecord(
            symbol=symbol,
            result=result,
            note=note,
            decision_date=decision_date,
            outcome_date=outcome_date,
        )
        self._outcome_store().append(row)
        return row

