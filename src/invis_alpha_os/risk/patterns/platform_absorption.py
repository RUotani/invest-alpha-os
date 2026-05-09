from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformAbsorptionPattern:
    detected: bool = False
    note: str = "stub: implement platform absorption detection in later phases"

