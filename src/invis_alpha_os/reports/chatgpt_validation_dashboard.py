"""Dashboard builders for benchmark-relative validation outputs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationDashboardResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _avg(vals: list[float]) -> float | None:
    return (sum(vals) / len(vals)) if vals else None


def _pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"


def build_validation_dashboard(*, as_of_date: str, horizon_rows: dict[str, list[dict[str, Any]]]) -> ValidationDashboardResult:
    sections: dict[str, dict[str, Any]] = {}
    class_agg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    timing_agg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    trap_agg: dict[str, list[dict[str, Any]]] = defaultdict(list)
    benchmark_available = 0
    evaluated_count = 0

    for horizon in ("4w", "12w", "26w"):
        rows = horizon_rows.get(horizon, [])
        cand_rets = [float(r["candidate_return_pct"]) for r in rows if isinstance(r.get("candidate_return_pct"), (int, float))]
        bench_rets = [float(r["benchmark_return_pct"]) for r in rows if isinstance(r.get("benchmark_return_pct"), (int, float))]
        excess = [float(r["excess_return_pct"]) for r in rows if isinstance(r.get("excess_return_pct"), (int, float))]
        hit = len([r for r in rows if str(r.get("result_label")) in ("strong_hit", "hit")])
        strong = len([r for r in rows if str(r.get("result_label")) == "strong_hit"])
        miss = len([r for r in rows if str(r.get("result_label")) in ("miss", "false_positive")])
        fp = len([r for r in rows if str(r.get("result_label")) == "false_positive"])
        fn = len([r for r in rows if str(r.get("result_label")) == "false_negative"])
        sections[horizon] = {
            "count": len(rows),
            "avg_candidate_return_pct": _avg(cand_rets),
            "avg_benchmark_return_pct": _avg(bench_rets),
            "avg_excess_return_pct": _avg(excess),
            "hit_rate": (hit / len(rows)) if rows else 0.0,
            "strong_hit_rate": (strong / len(rows)) if rows else 0.0,
            "miss_rate": (miss / len(rows)) if rows else 0.0,
            "false_positive_count": fp,
            "false_negative_count": fn,
        }
        for row in rows:
            evaluated_count += 1
            if isinstance(row.get("benchmark_return_pct"), (int, float)):
                benchmark_available += 1
            class_agg[str(row.get("classification", "不明"))].append(row)
            timing_agg[str(row.get("timing", "不明"))].append(row)
            for trap in (row.get("trap_flags") or []):
                trap_agg[str(trap)].append(row)

    def _table_rows(groups: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for key, rows in sorted(groups.items(), key=lambda x: x[0]):
            exc = [float(r["excess_return_pct"]) for r in rows if isinstance(r.get("excess_return_pct"), (int, float))]
            hit = len([r for r in rows if str(r.get("result_label")) in ("strong_hit", "hit")])
            fp = len([r for r in rows if str(r.get("result_label")) == "false_positive"])
            fn = len([r for r in rows if str(r.get("result_label")) == "false_negative"])
            out.append(
                {
                    "key": key,
                    "count": len(rows),
                    "avg_excess_return_pct": _avg(exc),
                    "hit_rate": (hit / len(rows)) if rows else 0.0,
                    "false_positive_count": fp,
                    "false_negative_count": fn,
                }
            )
        return out

    class_rows = _table_rows(class_agg)
    timing_rows = _table_rows(timing_agg)
    trap_rows = _table_rows(trap_agg)
    bench_rate = (benchmark_available / evaluated_count) if evaluated_count else 0.0

    lines = [
        "# Forward Validation Dashboard",
        "",
        "## メタ情報",
        f"- 評価基準日: {as_of_date}",
        f"- 評価済み候補数: {evaluated_count}",
        f"- benchmark利用率: {bench_rate * 100:.1f}%",
        "",
    ]
    for horizon in ("4w", "12w", "26w"):
        s = sections[horizon]
        lines.extend(
            [
                f"## {horizon}評価",
                f"- 平均候補リターン: {_pct(s['avg_candidate_return_pct'])}",
                f"- 平均benchmarkリターン: {_pct(s['avg_benchmark_return_pct'])}",
                f"- 平均超過リターン: {_pct(s['avg_excess_return_pct'])}",
                f"- hit rate: {s['hit_rate'] * 100:.1f}%",
                f"- strong hit rate: {s['strong_hit_rate'] * 100:.1f}%",
                f"- miss rate: {s['miss_rate'] * 100:.1f}%",
                f"- false positive: {s['false_positive_count']}",
                f"- false negative: {s['false_negative_count']}",
                "",
            ]
        )
    lines.extend(["## 分類別成績", "| 分類 | 件数 | 平均超過 | Hit率 | FP | FN |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in class_rows:
        lines.append(f"| {r['key']} | {r['count']} | {_pct(r['avg_excess_return_pct'])} | {r['hit_rate']*100:.1f}% | {r['false_positive_count']} | {r['false_negative_count']} |")
    lines.extend(["", "## timing別成績", "| Timing | 件数 | 平均超過 | Hit率 | FP | FN |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for r in timing_rows:
        lines.append(f"| {r['key']} | {r['count']} | {_pct(r['avg_excess_return_pct'])} | {r['hit_rate']*100:.1f}% | {r['false_positive_count']} | {r['false_negative_count']} |")
    lines.extend(["", "## trap warning別成績", "| Trap | 件数 | 平均超過 | Hit率 | コメント |", "| --- | ---: | ---: | ---: | --- |"])
    for r in trap_rows:
        comment = "件数小" if r["count"] < 3 else "要観察"
        lines.append(f"| {r['key']} | {r['count']} | {_pct(r['avg_excess_return_pct'])} | {r['hit_rate']*100:.1f}% | {comment} |")
    lines.extend(["", "## 改善示唆", "- benchmark未取得候補の低減を優先。", "- false_positive多発分類の閾値を再調整。", ""])

    payload = {
        "as_of_date": as_of_date,
        "sections": sections,
        "classification_summary": class_rows,
        "timing_summary": timing_rows,
        "trap_summary": trap_rows,
        "benchmark_coverage_rate": bench_rate,
    }
    return ValidationDashboardResult(markdown_text="\n".join(lines), json_payload=payload)

