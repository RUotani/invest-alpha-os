from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from invis_alpha_os.core.models import VetoLevel, VetoResult


def format_veto_table_cell(veto_result: Any) -> str:
    """`veto_result`（`signals` JSON の `_veto_row` 形式）から Markdown 表用の Veto セル文字列を返す。"""
    if not isinstance(veto_result, dict):
        return "—"
    if not veto_result.get("triggered"):
        return "—"
    rules = veto_result.get("rules")
    if not isinstance(rules, list):
        return "—"
    ids = [str(d.get("rule_id", "")) for d in rules if isinstance(d, dict) and d.get("rule_id")]
    if not ids:
        return "—"
    return "⚠ " + ", ".join(ids)


def veto_hits_to_result_dict(hits: list[VetoResult]) -> dict[str, Any]:
    """Serialize ``VetoEngine`` hits to the canonical ``veto_result`` dict (signals JSON)."""

    return {
        "triggered": len(hits) > 0,
        "count": len(hits),
        "rules": [
            {"level": v.level, "rule_id": v.rule_id, "message": v.message} for v in hits
        ],
    }


def build_momentum_veto_result(m: Any, engine: VetoEngine) -> dict[str, Any]:
    """Evaluate a momentum row and return the canonical ``veto_result`` dict."""

    return veto_hits_to_result_dict(engine.evaluate(momentum_breakdown_veto_context(m)))


def momentum_breakdown_veto_context(m: Any) -> dict[str, float]:
    """MomentumBreakdown 相当オブジェクトから VetoEngine 用の float コンテキストを組み立てる。"""
    r5 = float(m.r5 or 0.0)
    vr = m.volume_ratio_25d
    # R6.8-F: 出来高急増単独は避け、25日平均比 >= 3.0 かつ直近5日リターンが正で > 15% のときのみ 1.0
    vol_price_chase = 0.0
    if vr is not None and float(vr) >= 3.0 and r5 > 0.15:
        vol_price_chase = 1.0
    return {
        "price_spike_5d": abs(r5),
        "overheat_flag": 1.0 if bool(getattr(m, "overheat_flag", False)) else 0.0,
        "fomo_volume_price_chase": vol_price_chase,
    }


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

