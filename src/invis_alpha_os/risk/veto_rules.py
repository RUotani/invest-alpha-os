from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.core.models import VetoLevel, VetoResult


@dataclass(frozen=True)
class VetoEngine:
    rules: dict[str, Any]

    def evaluate(self, context: dict[str, Any]) -> list[VetoResult]:
        results: list[VetoResult] = []
        level_map = {
            "hard_veto": VetoLevel.hard_veto,
            "soft_veto": VetoLevel.soft_veto,
            "fomo_veto": VetoLevel.fomo_veto,
        }
        for level_name, level in level_map.items():
            for rule in self.rules.get(level_name, []):
                threshold = float(rule.get("threshold", 1.0))
                metric_key = str(rule.get("metric", ""))
                metric_val = float(context.get(metric_key, 0.0))
                if metric_val >= threshold:
                    results.append(
                        VetoResult(
                            level=level,
                            rule_id=str(rule.get("id", "unnamed_rule")),
                            message=str(rule.get("message", "veto triggered")),
                            evidence_ids=[],
                        )
                    )
        return results

