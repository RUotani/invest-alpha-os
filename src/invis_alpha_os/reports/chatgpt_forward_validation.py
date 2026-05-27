"""Forward validation seed/result generation from context candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

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
    result_paths: dict[str, Path] = {}
    seed_files = sorted(seeds_dir.glob("**/decision_seed.json"))
    horizons = {"4w": "plus_4w", "12w": "plus_12w", "26w": "plus_26w"}
    summary_lines = ["# Forward Validation Dashboard", "", f"- as_of_date: {as_of_date}", ""]
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
                if not isinstance(base_close, (int, float)) or now_close is None or base_close == 0:
                    ret = None
                else:
                    ret = now_close / float(base_close) - 1.0
                label = "hit" if isinstance(ret, float) and ret > 0 else "miss"
                all_rows.append(
                    {
                        "report_date": report_date,
                        "evaluation_horizon": hz_label,
                        "evaluated_at": as_of_date,
                        "ticker": ticker,
                        "return_pct": ret,
                        "result_label": label,
                    }
                )
        out_path = out_dir / "results" / as_of_date[:4] / as_of_date / f"result_{hz_label}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"as_of_date": as_of_date, "horizon": hz_label, "candidates": all_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        result_paths[f"result_{hz_label}"] = out_path
        n = len(all_rows)
        hit = len([x for x in all_rows if x.get("result_label") == "hit"])
        summary_lines.append(f"## {hz_label}結果")
        summary_lines.append(f"- hit rate: {hit}/{n}" if n else "- hit rate: 0/0")
        summary_lines.append("")
    dashboard = out_dir / "summary" / "validation_dashboard.md"
    dashboard.parent.mkdir(parents=True, exist_ok=True)
    dashboard.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    result_paths["dashboard"] = dashboard
    return result_paths
