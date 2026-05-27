"""Rule-based trap analysis for context pack candidates."""

from __future__ import annotations

from typing import Any


def _pct(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


def _level(score: int) -> str:
    if score >= 4:
        return "高"
    if score >= 2:
        return "中"
    return "低"


def analyze_candidate_traps(candidate: dict[str, Any]) -> dict[str, Any]:
    ma = candidate.get("moving_averages") or {}
    returns = candidate.get("returns") or {}
    rng = candidate.get("range_52w") or {}
    vol = candidate.get("volume") or {}
    freshness = str(candidate.get("freshness", ""))

    dist25 = _pct(ma.get("dist_ma25_pct"))
    dist75 = _pct(ma.get("dist_ma75_pct"))
    dist200 = _pct(ma.get("dist_ma200_pct"))
    ret5 = _pct(returns.get("d5"))
    ret60 = _pct(returns.get("d60"))
    dist_high = _pct(rng.get("dist_high_pct"))
    ratio20 = _pct(vol.get("ratio20"))

    value_trap_score = 0
    if dist200 is not None and dist200 < 0:
        value_trap_score += 1
    if ret60 is not None and ret60 < 0:
        value_trap_score += 1
    if dist_high is not None and dist_high < -0.2:
        value_trap_score += 1
    if ratio20 is not None and ratio20 > 1.5 and (ret5 is not None and ret5 < 0):
        value_trap_score += 1
    if "要更新" in freshness:
        value_trap_score += 1

    overheat_score = 0
    if dist25 is not None and dist25 > 0.1:
        overheat_score += 1
    if dist75 is not None and dist75 > 0.15:
        overheat_score += 1
    if ret5 is not None and ret5 > 0.08:
        overheat_score += 1
    if ratio20 is not None and ratio20 > 1.8:
        overheat_score += 1
    if dist_high is not None and dist_high > 0:
        overheat_score += 1

    early_sell_score = 0
    if dist25 is not None and dist25 > 0:
        early_sell_score += 1
    if dist75 is not None and dist75 > 0:
        early_sell_score += 1
    if dist200 is not None and dist200 > 0:
        early_sell_score += 1
    if ret60 is not None and ret60 > 0:
        early_sell_score += 1

    late_sell_score = 0
    if dist25 is not None and dist25 < 0:
        late_sell_score += 1
    if dist75 is not None and dist75 < 0:
        late_sell_score += 1
    if ret60 is not None and ret60 < 0:
        late_sell_score += 1
    if ratio20 is not None and ratio20 > 1.5 and (ret5 is not None and ret5 < 0):
        late_sell_score += 1

    upside: list[str] = []
    downside: list[str] = []
    if ret60 is not None and ret60 > 0:
        upside.append("中期モメンタムが維持")
    if dist200 is not None and dist200 > 0:
        upside.append("200日線より上で推移")
    if dist25 is not None and dist25 < 0.03 and dist25 > -0.05:
        upside.append("短期過熱が限定的")

    if ret60 is not None and ret60 < 0:
        downside.append("60日騰落率が弱い")
    if dist200 is not None and dist200 < 0:
        downside.append("200日線を下回る")
    if "要更新" in freshness:
        downside.append("データ鮮度が低い")

    return {
        "ticker": candidate.get("ticker", ""),
        "value_trap_risk": {"level": _level(value_trap_score), "score": value_trap_score},
        "overheat_risk": {"level": _level(overheat_score), "score": overheat_score},
        "early_sell_risk": {"level": _level(early_sell_score), "score": early_sell_score},
        "late_sell_risk": {"level": _level(late_sell_score), "score": late_sell_score},
        "upside_thesis": upside or ["追加入力待ち"],
        "downside_thesis": downside or ["追加入力待ち"],
        "invalidation_conditions": ["75日線割れ継続", "相対強度低下が継続"],
        "next_review_conditions": ["出来高と移動平均乖離の再確認", "benchmark相対で再評価"],
    }
