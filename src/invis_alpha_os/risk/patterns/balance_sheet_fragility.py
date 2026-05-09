from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BalanceSheetFragilityPattern:
    detected: bool = False
    note: str = "stub: implement fragility diagnostics in later phases"

