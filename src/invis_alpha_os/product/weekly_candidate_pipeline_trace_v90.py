"""Candidate pipeline traceability helpers for weekly brief v90."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CandidateTraceInput:
    symbol: str
    name: str | None = None
    has_required_coverage: bool = False
    score: float | None = None
    score_threshold: float = 0.0
    veto_reasons: tuple[str, ...] = ()
    data_insufficient_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class VetoReasonLog:
    symbol: str
    veto_key: str
    description_ja: str
    next_check_ja: str


@dataclass(frozen=True)
class CandidatePipelineTraceSummary:
    input_count: int
    coverage_ok_count: int
    coverage_missing_count: int
    score_pass_count: int
    score_miss_count: int
    veto_count: int
    final_candidate_count: int
    data_insufficient_count: int
    veto_reason_log: tuple[VetoReasonLog, ...]
    coverage_missing_symbols: tuple[str, ...]
    score_miss_symbols: tuple[str, ...]


_VETO_REASON_MAP: dict[str, tuple[str, str]] = {
    "overheated_caution": (
        "短期過熱のため追いかけ判断を抑制",
        "価格乖離・出来高・移動平均との距離を確認",
    ),
    "overheat_caution": (
        "短期過熱のため追いかけ判断を抑制",
        "価格乖離・出来高・移動平均との距離を確認",
    ),
    "low_liquidity_caution": (
        "流動性不足のため短期の値動き歪みを警戒",
        "出来高水準・スプレッド・板状況を確認",
    ),
}


def _normalize_veto_key(raw: str) -> str:
    key = raw.strip()
    return key if key else "unknown_veto"


def _veto_reason_parts(veto_key: str) -> tuple[str, str]:
    if veto_key in _VETO_REASON_MAP:
        return _VETO_REASON_MAP[veto_key]
    return (
        "安全側の除外条件に該当",
        "veto条件の定義と直近データの一致を確認",
    )


def build_candidate_pipeline_trace_summary(
    inputs: Iterable[CandidateTraceInput],
) -> CandidatePipelineTraceSummary:
    coverage_missing_symbols: list[str] = []
    score_miss_symbols: list[str] = []
    veto_reason_log: list[VetoReasonLog] = []

    coverage_ok_count = 0
    coverage_missing_count = 0
    score_pass_count = 0
    score_miss_count = 0
    veto_count = 0
    final_candidate_count = 0
    data_insufficient_count = 0

    input_count = 0
    for row in inputs:
        input_count += 1
        coverage_missing = (not row.has_required_coverage) or bool(row.data_insufficient_reasons)
        if row.data_insufficient_reasons:
            data_insufficient_count += 1
        if coverage_missing:
            coverage_missing_count += 1
            coverage_missing_symbols.append(row.symbol)
        else:
            coverage_ok_count += 1

        score_pass = False
        if not coverage_missing and row.score is not None:
            score_pass = row.score >= row.score_threshold
            if score_pass:
                score_pass_count += 1
            else:
                score_miss_count += 1
                score_miss_symbols.append(row.symbol)

        has_veto = len(row.veto_reasons) > 0
        if has_veto:
            veto_count += 1
            for reason in row.veto_reasons:
                veto_key = _normalize_veto_key(reason)
                desc, next_check = _veto_reason_parts(veto_key)
                veto_reason_log.append(
                    VetoReasonLog(
                        symbol=row.symbol,
                        veto_key=veto_key,
                        description_ja=desc,
                        next_check_ja=next_check,
                    )
                )

        if score_pass and not has_veto:
            final_candidate_count += 1

    return CandidatePipelineTraceSummary(
        input_count=input_count,
        coverage_ok_count=coverage_ok_count,
        coverage_missing_count=coverage_missing_count,
        score_pass_count=score_pass_count,
        score_miss_count=score_miss_count,
        veto_count=veto_count,
        final_candidate_count=final_candidate_count,
        data_insufficient_count=data_insufficient_count,
        veto_reason_log=tuple(veto_reason_log),
        coverage_missing_symbols=tuple(coverage_missing_symbols),
        score_miss_symbols=tuple(score_miss_symbols),
    )
