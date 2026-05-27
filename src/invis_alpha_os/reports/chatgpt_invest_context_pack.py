"""Build ChatGPT context pack from weekly candidate brief artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import compute_candidate_quant_metrics


@dataclass(frozen=True)
class ContextPackResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _brief_json_path(report_dir: Path) -> Path:
    return report_dir / "weekly_candidate_brief_v0_1.json"


def _read_brief_payload(report_dir: Path) -> dict[str, Any]:
    path = _brief_json_path(report_dir)
    if not path.is_file():
        raise FileNotFoundError(f"weekly_candidate_brief_v0_1.json が見つかりません: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("weekly brief json の形式が不正です")
    return data


def _to_candidate_item(row: dict[str, Any], *, rank: int, report_date: str) -> dict[str, Any]:
    cand = row.get("candidate") or {}
    symbol = str(cand.get("instrument_id", "")).strip()
    market = str(cand.get("market", "")).strip() or "US"
    qm = compute_candidate_quant_metrics(symbol=symbol, market=market, report_date=report_date)
    return {
        "rank": rank,
        "ticker": symbol,
        "name": str(cand.get("display_name", "")),
        "market": market,
        "classification": str(row.get("brief_type", "")),
        "timing": "要確認",
        "theme": ",".join(str(x) for x in (cand.get("themes") or [])),
        "latest_close": qm.latest_close,
        "latest_bar_date": qm.latest_bar_date,
        "freshness": qm.freshness_label,
        "returns": {"d5": qm.ret_5d_pct, "d20": qm.ret_20d_pct, "d60": qm.ret_60d_pct},
        "moving_averages": {
            "ma25": qm.ma_25,
            "ma75": qm.ma_75,
            "ma200": qm.ma_200,
            "dist_ma25_pct": qm.dist_ma_25_pct,
            "dist_ma75_pct": qm.dist_ma_75_pct,
            "dist_ma200_pct": qm.dist_ma_200_pct,
        },
        "range_52w": {
            "high": qm.high_52w,
            "low": qm.low_52w,
            "dist_high_pct": qm.dist_52w_high_pct,
            "dist_low_pct": qm.dist_52w_low_pct,
        },
        "volume": {"latest": qm.latest_volume, "avg20": qm.avg_volume_20d, "ratio20": qm.volume_ratio_20d},
        "momentum_rationale": [str(row.get("reason", ""))],
        "counter_evidence": [str(x) for x in (row.get("counter_evidence") or [])],
        "next_checks": [str(x) for x in (row.get("next_checks") or [])],
        "chatgpt_questions": [
            "この銘柄の上昇シナリオと無効化条件を3つずつ整理してください。",
            "今週の監視ポイントを優先順位付きで示してください。",
        ],
        "missing_data_reasons": [qm.missing_reason] if qm.missing_reason else [],
        "sources": [qm.source, "weekly_candidate_brief_v0_1.json"],
    }


def build_chatgpt_context_pack(*, report_date: str, report_dir: Path) -> ContextPackResult:
    payload = _read_brief_payload(report_dir)
    sections = payload.get("sections") or {}
    top = sections.get("top_picks") or []
    top10 = [_to_candidate_item(row, rank=i + 1, report_date=report_date) for i, row in enumerate(top[:10]) if isinstance(row, dict)]
    rapid = sections.get("rapid_movers") or []
    pull = sections.get("pullbacks") or []
    avoid = sections.get("avoid") or []
    insuf = sections.get("insufficient") or []

    out_json: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "source": "weekly_candidate_brief",
        "language": "ja",
        "disclaimer": "投資助言ではなく、観測・検証用です",
        "market_regime": {"label": "未実装", "notes": ["次PRで市場レジーム判定を追加予定"]},
        "summary": {
            "a_candidates": [c["ticker"] for c in top10[:3]],
            "b_candidates": [c["ticker"] for c in top10[3:6]],
            "watch_candidates": [c["ticker"] for c in top10[6:10]],
            "skip_candidates": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in avoid[:5] if isinstance(x, dict)],
            "data_insufficient": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in insuf[:5] if isinstance(x, dict)],
            "main_themes": [str(x.get("reason", "")) for x in top[:3] if isinstance(x, dict)],
            "main_risks": [str((x.get("counter_evidence") or [""])[0]) for x in top[:3] if isinstance(x, dict)],
        },
        "candidates": top10,
        "research_queue": {
            "today": [c["ticker"] for c in top10[:3]],
            "pullback_watch": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in pull[:5] if isinstance(x, dict)],
            "breakout_watch": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in rapid[:5] if isinstance(x, dict)],
            "skip": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in avoid[:5] if isinstance(x, dict)],
            "data_insufficient": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in insuf[:5] if isinstance(x, dict)],
        },
        "week_over_week_changes": {
            "new": ["未実装"],
            "up": ["未実装"],
            "down": ["未実装"],
            "removed": ["未実装"],
            "continued": ["未実装"],
        },
    }

    md_lines: list[str] = [
        "# ChatGPT投資対話用Context Pack",
        "",
        "## 0. メタ情報",
        f"- レポート日: {report_date}",
        f"- 生成日時: {out_json['generated_at']}",
        "- データ鮮度: 候補ごとの定量スナップショットを参照",
        "- 対象市場: JP / US / ETF",
        "- 生成元: weekly_candidate_brief_v0_1.json",
        "- 注意書き: 投資助言ではなく、観測・検証用です",
        "",
        "## 1. 今週の結論",
        f"- A候補: {', '.join(out_json['summary']['a_candidates']) or 'なし'}",
        f"- B候補: {', '.join(out_json['summary']['b_candidates']) or 'なし'}",
        f"- 見送り候補: {', '.join(out_json['summary']['skip_candidates']) or 'なし'}",
        f"- データ不足候補: {', '.join(out_json['summary']['data_insufficient']) or 'なし'}",
        "- 今週の主要テーマ: 候補理由を参照",
        "- 最大の注意点: stale/データ不足理由を優先確認",
        "",
        "## 2. 市場レジーム",
        "- レジーム判定: 未実装",
        "- 補足: 次PRで追加予定",
        "",
        "## 3. 注目候補Top10",
    ]
    for c in top10:
        md_lines.extend(
            [
                f"### {c['rank']}. {c['ticker']} — {c['name']}",
                f"- 分類: {c['classification']}",
                f"- 直近終値: {c['latest_close']}",
                f"- 直近データ日: {c['latest_bar_date']}",
                f"- データ鮮度: {c['freshness']}",
                f"- 5D/20D/60D騰落率: {c['returns']['d5']}, {c['returns']['d20']}, {c['returns']['d60']}",
                f"- 25D/75D/200D移動平均線との乖離: {c['moving_averages']['dist_ma25_pct']}, {c['moving_averages']['dist_ma75_pct']}, {c['moving_averages']['dist_ma200_pct']}",
                f"- 52週高値/安値との距離: {c['range_52w']['dist_high_pct']}, {c['range_52w']['dist_low_pct']}",
                f"- 出来高倍率: {c['volume']['ratio20']}",
                f"- モメンタム根拠: {', '.join(c['momentum_rationale']) or 'なし'}",
                f"- 反証・下落リスク: {', '.join(c['counter_evidence']) or 'なし'}",
                f"- 次に確認すること: {', '.join(c['next_checks']) or 'なし'}",
                f"- このチャットで議論したい問い: {', '.join(c['chatgpt_questions'])}",
                "",
            ]
        )
    md_lines.extend(
        [
            "## 4. 深掘り優先キュー",
            "### 今日見る",
            *[f"{i+1}. {s}" for i, s in enumerate(out_json["research_queue"]["today"][:3])],
            "",
            "### 押し目待ち",
            *[f"- {s}" for s in out_json["research_queue"]["pullback_watch"][:5]],
            "",
            "### ブレイクアウト監視",
            *[f"- {s}" for s in out_json["research_queue"]["breakout_watch"][:5]],
            "",
            "### 見送り",
            *[f"- {s}" for s in out_json["research_queue"]["skip"][:5]],
            "",
            "## 5. 前週からの変化",
            "- 未実装（次PR候補）",
            "",
            "## 6. 欠損・注意データ",
            "- stale: 候補ごとのデータ鮮度を参照",
            "- cache不足: missing_data_reasons を参照",
            "",
            "## 7. ChatGPTへの推奨質問",
            "- 上位3銘柄の無効化条件を先に定義してください。",
            "- staleデータ銘柄を除いた場合の優先順位を提案してください。",
            "",
        ]
    )
    return ContextPackResult(markdown_text="\n".join(md_lines).rstrip() + "\n", json_payload=out_json)

