"""Forward validation seed/result generation from context candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.chatgpt_benchmark_mapping import infer_benchmark_for_candidate
from invis_alpha_os.reports.chatgpt_validation_dashboard import build_validation_dashboard
from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache
from invis_alpha_os.data.us_daily_bars_cache import load_us_daily_bars_cache


def _add_weeks(d: str, weeks: int) -> str:
    return (date.fromisoformat(d) + timedelta(days=weeks * 7)).isoformat()


def _load_close(symbol: str, market: str, as_of: str) -> float | None:
    loaded = load_jquants_daily_bars_cache(symbol) if market == "JP" else load_us_daily_bars_cache(symbol)
    if loaded is None:
        return None
    bars = loaded[0]
    close = None
    for bar in bars:
        bar_date = str(bar.get("date", ""))
        if bar_date <= as_of:
            close = float(bar.get("close", 0.0))
    return close


def _load_close_any_market(symbol: str, as_of: str) -> tuple[float | None, str]:
    market_hint = "JP" if symbol in ("TOPIX", "^TOPX", "1306", "1321", "^N225") else "US"
    close = _load_close(symbol, market_hint, as_of)
    if close is not None:
        return close, market_hint
    alt = "US" if market_hint == "JP" else "JP"
    return _load_close(symbol, alt, as_of), alt


def _label_from_metrics(*, excess_return_pct: float | None, classification: str, timing: str) -> str:
    if excess_return_pct is None:
        return "data_insufficient"
    cls = classification.lower()
    tmg = timing.lower()
    if ("深掘り" in classification or cls.startswith("a")) and excess_return_pct <= -0.05:
        return "false_positive"
    if ("見送り" in classification or "見送り" in timing or "low" in cls or "skip" in cls) and excess_return_pct >= 0.10:
        return "false_negative"
    if excess_return_pct >= 0.05:
        return "strong_hit"
    if excess_return_pct > 0:
        return "hit"
    if -0.02 <= excess_return_pct <= 0:
        return "neutral"
    if excess_return_pct < -0.02:
        return "miss"
    _ = tmg
    return "neutral"


@dataclass(frozen=True)
class ValidationSeedResult:
    markdown_text: str
    json_payload: dict[str, Any]


def build_validation_seed(*, report_date: str, context_json_payload: dict[str, Any]) -> ValidationSeedResult:
    eval_dates = {"plus_4w": _add_weeks(report_date, 4), "plus_12w": _add_weeks(report_date, 12), "plus_26w": _add_weeks(report_date, 26)}
    candidates = context_json_payload.get("candidates")
    rows = [x for x in candidates if isinstance(x, dict)] if isinstance(candidates, list) else []
    out: list[dict[str, Any]] = []
    md = ["# decision_seed", "", f"- report_date: {report_date}", ""]
    for row in rows:
        item = {
            "ticker": row.get("ticker", ""),
            "name": row.get("name", ""),
            "market": row.get("market", "US"),
            "rank": row.get("rank"),
            "classification": row.get("classification", ""),
            "timing": row.get("timing", ""),
            "latest_close_at_report": row.get("latest_close"),
            "latest_bar_date": row.get("latest_bar_date", ""),
            "benchmark": "SPY" if row.get("market") == "US" else "TOPIX",
            "future_evaluation_dates": eval_dates,
        }
        out.append(item)
        md.append(f"- {item['ticker']} ({item['classification']})")
    payload = {"report_date": report_date, "evaluation_dates": eval_dates, "candidates": out}
    return ValidationSeedResult(markdown_text="\n".join(md) + "\n", json_payload=payload)


def evaluate_validation_seeds(*, as_of_date: str, seeds_dir: Path, out_dir: Path) -> dict[str, Path]:
    results_root = out_dir if out_dir.name == "results" else out_dir / "results"
    result_paths: dict[str, Path] = {}
    seed_files = sorted(seeds_dir.glob("**/decision_seed.json"))
    horizons = {"4w": "plus_4w", "12w": "plus_12w", "26w": "plus_26w"}
    horizon_rows: dict[str, list[dict[str, Any]]] = {}
    for hz_label, hz_key in horizons.items():
        all_rows: list[dict[str, Any]] = []
        for seed in seed_files:
            payload = json.loads(seed.read_text(encoding="utf-8"))
            report_date = str(payload.get("report_date", ""))
            for row in payload.get("candidates", []):
                if not isinstance(row, dict):
                    continue
                eval_date = str((row.get("future_evaluation_dates") or {}).get(hz_key, ""))
                if not eval_date or eval_date > as_of_date:
                    continue
                market = str(row.get("market", "US"))
                ticker = str(row.get("ticker", ""))
                base_close = row.get("latest_close_at_report")
                now_close = _load_close(ticker, market, as_of_date)
                candidate_return = None
                if isinstance(base_close, (int, float)) and now_close is not None and base_close != 0:
                    candidate_return = now_close / float(base_close) - 1.0

                benchmark_ticker = str(row.get("benchmark", "")).strip() or infer_benchmark_for_candidate(
                    market=market,
                    ticker=ticker,
                )
                benchmark_report_close = None
                benchmark_eval_close = None
                benchmark_return = None
                benchmark_missing_reason = None
                if benchmark_ticker:
                    benchmark_report_close, _ = _load_close_any_market(benchmark_ticker, report_date)
                    benchmark_eval_close, _ = _load_close_any_market(benchmark_ticker, as_of_date)
                    if (
                        isinstance(benchmark_report_close, (int, float))
                        and isinstance(benchmark_eval_close, (int, float))
                        and benchmark_report_close != 0
                    ):
                        benchmark_return = benchmark_eval_close / benchmark_report_close - 1.0
                    else:
                        benchmark_missing_reason = "benchmark_price_missing"
                else:
                    benchmark_missing_reason = "benchmark_unavailable"
                excess_return = (
                    candidate_return - benchmark_return
                    if isinstance(candidate_return, float) and isinstance(benchmark_return, float)
                    else None
                )
                classification = str(row.get("classification", ""))
                timing = str(row.get("timing", ""))
                label = _label_from_metrics(
                    excess_return_pct=excess_return,
                    classification=classification,
                    timing=timing,
                )
                trap_flags = [str(x) for x in (row.get("trap_flags") or [])]
                all_rows.append(
                    {
                        "report_date": report_date,
                        "evaluation_horizon": hz_label,
                        "evaluated_at": as_of_date,
                        "ticker": ticker,
                        "classification": classification,
                        "timing": timing,
                        "candidate_return_pct": candidate_return,
                        "benchmark_ticker": benchmark_ticker,
                        "benchmark_return_pct": benchmark_return,
                        "excess_return_pct": excess_return,
                        "benchmark_missing_reason": benchmark_missing_reason,
                        "trap_flags": trap_flags,
                        "result_label": label,
                    }
                )
        out_path = results_root / as_of_date[:4] / as_of_date / f"result_{hz_label}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"as_of_date": as_of_date, "horizon": hz_label, "candidates": all_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        result_paths[f"result_{hz_label}"] = out_path
        horizon_rows[hz_label] = all_rows
    dashboard = build_validation_dashboard(as_of_date=as_of_date, horizon_rows=horizon_rows)
    dashboard_md = out_dir / "validation_dashboard.md"
    dashboard_json = out_dir / "validation_dashboard.json"
    dashboard_md.parent.mkdir(parents=True, exist_ok=True)
    dashboard_md.write_text(dashboard.markdown_text, encoding="utf-8")
    dashboard_json.write_text(json.dumps(dashboard.json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result_paths["dashboard_md"] = dashboard_md
    result_paths["dashboard_json"] = dashboard_json
    return result_paths
