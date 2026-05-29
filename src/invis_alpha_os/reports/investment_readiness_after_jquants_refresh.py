"""Post–J-Quants refresh investment readiness re-evaluation (read-only, no live HTTP)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV

DEFAULT_JP_TARGETS = DEFAULT_TARGET_TICKERS_CSV
CONTRACT_DATA_TO = "2026-03-06"
PUBLIC_OHLCV_APPROVAL_PHRASE = "public OHLCV source live fetchを実行してよい"

_CLASSIFICATION_MAP = {
    "wait_for_pullback": "押し目待ち",
    "overheated_watch": "ブレイクアウト監視",
    "watch_breakout": "ブレイクアウト監視",
    "monitor": "ブレイクアウト監視",
    "deep_dive": "深掘り",
    "skip": "見送り",
    "insufficient": "データ不足",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _gap_days(report_date: str, latest_bar: str | None) -> int | None:
    if not latest_bar:
        return None
    try:
        return (date.fromisoformat(report_date) - date.fromisoformat(latest_bar)).days
    except ValueError:
        return None


def _candidate_by_ticker(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in context.get("candidates") or []:
        if isinstance(row, dict):
            t = str(row.get("ticker", "")).strip()
            if t:
                out[t] = row
    return out


def _trap_by_ticker(trap_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in trap_doc.get("trap_analysis") or []:
        if isinstance(row, dict):
            t = str(row.get("ticker", "")).strip()
            if t:
                out[t] = row
    return out


def _freshness_from_verification(verification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in verification.get("per_ticker") or []:
        if isinstance(row, dict):
            t = str(row.get("ticker", "")).strip()
            if t:
                out[t] = row
    return out


def _classify_ticker(
    *,
    ticker: str,
    candidate: dict[str, Any] | None,
    trap: dict[str, Any] | None,
    gap: int | None,
    freshness_status: str,
    in_skip: bool,
) -> dict[str, Any]:
    if in_skip and not candidate:
        return {
            "ticker": ticker,
            "classification": "見送り",
            "confidence": "低",
            "upside_factors": ["context packでskip候補"],
            "downside_factors": ["候補ランク外", "84日ギャップでタイミング不可"],
            "invalidation": ["テーマ悪化・需給悪化の確認（データ更新後）"],
            "data_gap_note": f"latest={CONTRACT_DATA_TO}, gap={gap}日（report基準）",
        }

    if not candidate:
        return {
            "ticker": ticker,
            "classification": "データ不足",
            "confidence": "低",
            "upside_factors": ["manual/cache coverageのみ"],
            "downside_factors": ["context pack候補行なし", "定量ランキング不可"],
            "invalidation": ["候補行追加後に再評価"],
            "data_gap_note": f"gap={gap}日" if gap is not None else "cache_missing",
        }

    timing = str(candidate.get("timing", ""))
    ctx_class = str(candidate.get("classification", ""))
    timing_ja = str(candidate.get("timing_label_ja", ""))
    base = _CLASSIFICATION_MAP.get(timing, "深掘り")
    if ctx_class == "top_pick" and timing in {"wait_for_pullback", "overheated_watch"}:
        if timing == "wait_for_pullback":
            base = "押し目待ち"
        else:
            base = "ブレイクアウト監視"

    overheat = (trap or {}).get("overheat_risk", {})
    overheat_level = str(overheat.get("level", "")) if isinstance(overheat, dict) else ""
    confidence = "中"
    if gap is not None and gap >= 60:
        confidence = "低"
    elif gap is not None and gap <= 14:
        confidence = "高"
    if overheat_level in {"高", "中"} and gap and gap > 30:
        confidence = "低"

    upside = list((trap or {}).get("upside_thesis") or [])[:3]
    if not upside:
        upside = list(candidate.get("momentum_rationale") or [])[:2]
    downside = list((trap or {}).get("downside_thesis") or [])[:3]
    if not downside:
        downside = list(candidate.get("counter_evidence") or [])[:2]
    invalidation = list((trap or {}).get("invalidation_conditions") or [])[:3]

    note = (
        f"latest={candidate.get('latest_bar_date', CONTRACT_DATA_TO)}; "
        f"gap={gap}日; timing={timing_ja or timing}; "
        "Post-2026-03価格なしのため短期売買断定不可"
    )
    return {
        "ticker": ticker,
        "classification": base,
        "confidence": confidence,
        "upside_factors": upside,
        "downside_factors": downside,
        "invalidation": invalidation,
        "data_gap_note": note,
    }


def _ohlcv_need_level(*, gap: int | None, classification: str, timing: str) -> tuple[str, str]:
    if gap is None:
        return "defer", "cache_missing"
    if gap <= 7:
        return "current_cache_sufficient_for_structural_view", "contract_to内でギャップ小"
    if classification in {"ブレイクアウト監視", "押し目待ち"}:
        return "must_have_recent_ohlcv", "momentum/breakout/timing判定にPost-2026-03 OHLCV必須"
    if classification == "深掘り":
        return "nice_to_have_recent_ohlcv", "テーマ深掘りはcache可、タイミング精度は低下"
    if classification == "見送り":
        return "defer", "優先度低"
    return "must_have_recent_ohlcv", f"gap={gap}日でforward/trap信頼度低下"


@dataclass(frozen=True)
class InvestmentReadinessV31Result:
    readiness_markdown: str
    readiness_json: dict[str, Any]
    classification_markdown: str
    classification_json: dict[str, Any]
    ohlcv_need_markdown: str
    ohlcv_need_json: dict[str, Any]
    alternative_export_markdown: str
    alternative_export_json: dict[str, Any]
    public_live_fetch_markdown: str
    public_live_fetch_json: dict[str, Any]
    no_immediate_action_markdown: str
    no_immediate_action_json: dict[str, Any]


def build_investment_readiness_v31(
    *,
    report_date: str,
    reports_latest_dir: Path,
    targets_csv: str = DEFAULT_JP_TARGETS,
) -> InvestmentReadinessV31Result:
    latest = reports_latest_dir
    context = _load_json(latest / "chatgpt_invest_context_pack.json")
    readiness = _load_json(latest / "cache_refresh_readiness.json")
    trap_doc = _load_json(latest / "trap_analysis.json")
    verification = _load_json(latest / "jquants_refresh_freshness_verification.json")
    dry_run = _load_json(latest / "manual_data_import_flow.json")
    validation = _load_json(latest / "validation_dashboard.json")
    if not validation:
        validation = _load_json(
            latest.parent / "validation" / "results" / "validation_dashboard.json"
        )

    targets = [t.strip() for t in targets_csv.split(",") if t.strip()]
    candidates = _candidate_by_ticker(context)
    traps = _trap_by_ticker(trap_doc)
    fresh = _freshness_from_verification(verification)
    skip_set = set(context.get("summary", {}).get("skip_candidates") or [])

    freshness_rows: list[dict[str, Any]] = []
    classification_rows: list[dict[str, Any]] = []
    ohlcv_rows: list[dict[str, Any]] = []

    for ticker in targets:
        cand = candidates.get(ticker)
        trap = traps.get(ticker)
        fv = fresh.get(ticker, {})
        latest_date = (
            str(cand.get("latest_bar_date"))
            if cand and cand.get("latest_bar_date")
            else str(fv.get("after_latest") or CONTRACT_DATA_TO)
        )
        gap = _gap_days(report_date, latest_date)
        status = str(fv.get("status") or "stale_vs_report_date")
        freshness_rows.append(
            {
                "ticker": ticker,
                "latest_date": latest_date,
                "gap_days": gap,
                "status": status,
            }
        )
        cls = _classify_ticker(
            ticker=ticker,
            candidate=cand,
            trap=trap,
            gap=gap,
            freshness_status=status,
            in_skip=ticker in skip_set,
        )
        classification_rows.append(cls)
        need, reason = _ohlcv_need_level(
            gap=gap,
            classification=cls["classification"],
            timing=str(cand.get("timing", "")) if cand else "",
        )
        ohlcv_rows.append({"ticker": ticker, "need_level": need, "reason": reason})

    must_have = [r["ticker"] for r in ohlcv_rows if r["need_level"] == "must_have_recent_ohlcv"]
    structural_ok = [
        r["ticker"]
        for r in ohlcv_rows
        if r["need_level"] == "current_cache_sufficient_for_structural_view"
    ]

    refresh_reflected = bool(verification.get("refresh_executed"))
    import_rows_newer = int(dry_run.get("rows_newer_than_cache_total") or 0)
    proceed_structural = len(must_have) == 0 or len(structural_ok) > 0

    readiness_payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v31",
        "context_pack_reflects_v30r_refresh": refresh_reflected,
        "validation_dashboard_usable": bool(validation.get("sections")),
        "validation_sample_counts": {
            k: (validation.get("sections") or {}).get(k, {}).get("count")
            for k in ("4w", "12w", "26w")
        },
        "trap_analysis_present": bool(trap_doc.get("trap_analysis")),
        "manual_import_recommended": False,
        "rows_newer_than_cache_total": import_rows_newer,
        "investment_readiness_verdict": (
            "proceed_structural_analysis_only"
            if proceed_structural and must_have
            else (
                "prioritize_post_contract_ohlcv"
                if must_have
                else "proceed_with_caution"
            )
        ),
        "must_have_recent_ohlcv_tickers": must_have,
        "structural_view_ok_tickers": structural_ok,
        "contract_data_available_to": CONTRACT_DATA_TO,
        "stale_vs_report_date_days_typical": 84,
        "secrets_printed": False,
    }

    classification_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "disclaimer": "投資助言ではなく、調査・監視優先順位",
        "per_ticker": classification_rows,
    }

    ohlcv_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "per_ticker": ohlcv_rows,
        "summary": {
            "must_have_recent_ohlcv": must_have,
            "nice_to_have": [r["ticker"] for r in ohlcv_rows if r["need_level"] == "nice_to_have_recent_ohlcv"],
            "structural_sufficient": structural_ok,
            "defer": [r["ticker"] for r in ohlcv_rows if r["need_level"] == "defer"],
        },
    }

    alt_export_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "package_status": "ready_for_manual_export" if must_have else "optional",
        "recommended_source": "yahoo_finance_jp_manual_export",
        "target_tickers": must_have or targets,
        "required_columns": ["ticker", "date", "open", "high", "low", "close", "volume"],
        "dropzone_filename": "manual_jp_bars.csv",
        "exact_next_commands": [
            "Export OHLCV-only from Yahoo Finance Japan",
            "Save to ~/Downloads/invest-alpha-os-manual-data-dropzone/manual_jp_bars.csv",
            "weekly-candidate-brief-manual-data-import-flow --input-path <path> (dry-run only until import approved)",
        ],
        "requires_user_approval_for_import": "manual JP bars actual importを実行してよい",
        "live_http_required": False,
        "secrets_printed": False,
    }

    public_fetch_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "package_status": "deferred_not_primary",
        "requires_user_approval": True,
        "required_approval_phrase": PUBLIC_OHLCV_APPROVAL_PHRASE,
        "note": "J-Quants contract capped at 2026-03-06; public live fetch is secondary to manual export",
        "live_http_required": True,
        "cache_write_required": True,
        "safety_checklist": {
            "live_http": False,
            "cache_write": False,
            "secrets_printed": False,
        },
    }

    no_action_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "package_status": "recommended_parallel_path",
        "recommendation": (
            "テーマ・バリューチェーン・無効化条件の構造分析は現cacheで継続可能。"
            "タイミング判断はPost-2026-03 OHLCV取得後。"
        ),
        "allowed_now": [
            "chatgpt_invest_context_packによる深掘り質問",
            "trap_analysis・テーマリスクの整理",
            "validation種蒔き（forward mature待ち）",
        ],
        "blocked_until_ohlcv": must_have,
        "secrets_printed": False,
    }

    def _md_readiness() -> str:
        lines = [
            "# Investment Readiness After J-Quants Refresh",
            "",
            f"- report_date: {report_date}",
            f"- verdict: {readiness_payload['investment_readiness_verdict']}",
            f"- v30r_refresh_reflected: {str(refresh_reflected).lower()}",
            f"- manual_import_recommended: false",
            f"- rows_newer_than_cache: {import_rows_newer}",
            "",
            "## Freshness",
            "",
            "| ticker | latest | gap_days | status |",
            "|---|---|---:|---|",
        ]
        for r in freshness_rows:
            lines.append(
                f"| {r['ticker']} | {r['latest_date']} | {r.get('gap_days', '-')} | {r['status']} |"
            )
        return "\n".join(lines)

    def _md_classification() -> str:
        lines = [
            "# Candidate Classification After Refresh",
            "",
            "| ticker | classification | confidence | data_gap_note |",
            "|---|---|---|---|",
        ]
        for r in classification_rows:
            note = str(r["data_gap_note"])
            if len(note) > 72:
                note = note[:69] + "..."
            lines.append(
                f"| {r['ticker']} | {r['classification']} | {r['confidence']} | {note} |"
            )
        return "\n".join(lines)

    def _md_ohlcv() -> str:
        lines = [
            "# Post-2026-03 OHLCV Need Assessment",
            "",
            "| ticker | need_level | reason |",
            "|---|---|---|",
        ]
        for r in ohlcv_rows:
            lines.append(f"| {r['ticker']} | {r['need_level']} | {r['reason']} |")
        return "\n".join(lines)

    return InvestmentReadinessV31Result(
        readiness_markdown=_md_readiness(),
        readiness_json=readiness_payload,
        classification_markdown=_md_classification(),
        classification_json=classification_payload,
        ohlcv_need_markdown=_md_ohlcv(),
        ohlcv_need_json=ohlcv_payload,
        alternative_export_markdown="# Alternative OHLCV Manual Export Package\n\n"
        f"- status: {alt_export_payload['package_status']}\n"
        f"- source: yahoo_finance_jp_manual_export\n"
        f"- targets: {', '.join(alt_export_payload['target_tickers'])}\n",
        alternative_export_json=alt_export_payload,
        public_live_fetch_markdown="# Public OHLCV Live Fetch Approval Package\n\n"
        f"- status: {public_fetch_payload['package_status']}\n"
        f"- phrase: {PUBLIC_OHLCV_APPROVAL_PHRASE}\n",
        public_live_fetch_json=public_fetch_payload,
        no_immediate_action_markdown="# No Immediate Data Action Recommendation\n\n"
        f"- {no_action_payload['recommendation']}\n",
        no_immediate_action_json=no_action_payload,
    )


def write_investment_readiness_v31_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: InvestmentReadinessV31Result,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    pairs = [
        ("investment_readiness_after_jquants_refresh", result.readiness_markdown, result.readiness_json),
        ("candidate_classification_after_refresh", result.classification_markdown, result.classification_json),
        ("post_2026_03_ohlcv_need_assessment", result.ohlcv_need_markdown, result.ohlcv_need_json),
        ("alternative_ohlcv_manual_export_package", result.alternative_export_markdown, result.alternative_export_json),
        ("public_ohlcv_live_fetch_approval_package", result.public_live_fetch_markdown, result.public_live_fetch_json),
        ("no_immediate_data_action_recommendation", result.no_immediate_action_markdown, result.no_immediate_action_json),
    ]
    for stem, md, js in pairs:
        lp = latest / f"{stem}.md"
        lj = latest / f"{stem}.json"
        wp = weekly / f"{stem}.md"
        wj = weekly / f"{stem}.json"
        lp.write_text(md, encoding="utf-8")
        lj.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
        wp.write_text(md, encoding="utf-8")
        wj.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"latest_{stem}_md"] = lp
        paths[f"latest_{stem}_json"] = lj
    return paths


def sync_investment_readiness_v31_to_reports_repo(
    *,
    reports_repo_path: Path,
    report_date: str,
    result: InvestmentReadinessV31Result,
) -> dict[str, Path]:
    out = reports_repo_path
    latest = out / "latest"
    weekly = out / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    pairs = [
        ("investment_readiness_after_jquants_refresh", result.readiness_markdown, result.readiness_json),
        ("candidate_classification_after_refresh", result.classification_markdown, result.classification_json),
        ("post_2026_03_ohlcv_need_assessment", result.ohlcv_need_markdown, result.ohlcv_need_json),
        ("alternative_ohlcv_manual_export_package", result.alternative_export_markdown, result.alternative_export_json),
        ("public_ohlcv_live_fetch_approval_package", result.public_live_fetch_markdown, result.public_live_fetch_json),
        ("no_immediate_data_action_recommendation", result.no_immediate_action_markdown, result.no_immediate_action_json),
    ]
    for stem, md, js in pairs:
        for label, root in (("reports_latest", latest), ("reports_weekly", weekly)):
            mp = root / f"{stem}.md"
            jp = root / f"{stem}.json"
            mp.write_text(md, encoding="utf-8")
            jp.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{stem}_md"] = mp
            paths[f"{label}_{stem}_json"] = jp
    return paths
