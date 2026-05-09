from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OverheatSignal:
    metric_name: str
    value: float
    threshold: float

    @property
    def is_overheated(self) -> bool:
        return self.value >= self.threshold

