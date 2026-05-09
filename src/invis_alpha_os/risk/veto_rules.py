from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.core.models import VetoLevel, VetoResult


@dataclass(frozen=True)
class VetoEngine:
    rules: dict[str, Any]

    def evaluate(self, context: dict[str, Any]) -> list[VetoResult]:
        results: list[VetoResult] = []
        for level_name in ("hard_veto", "soft_veto"):
            for rule in self.rules.get(level_name, []):
                threshold = float(rule.get("threshold", 1.0))
                metric_key = str(rule.get("metric", ""))
                metric_val = float(context.get(metric_key, 0.0))
                if metric_val >= threshold:
                    level = VetoLevel.hard_veto if level_name == "hard_veto" else VetoLevel.soft_veto
                    results.append(
                        VetoResult(
                            level=level,
                            rule_id=str(rule.get("id", "unnamed_rule")),
                            message=str(rule.get("message", "veto triggered")),
                            evidence_ids=[],
                        )
                    )
        return results

