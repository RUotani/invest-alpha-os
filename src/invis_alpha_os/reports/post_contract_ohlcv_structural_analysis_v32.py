"""v32: Post-contract OHLCV discovery, export quick guide, structural theme analysis (read-only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.chatgpt_trap_analysis import analyze_candidate_traps
from invis_alpha_os.reports.investment_readiness_after_jquants_refresh import (
    CONTRACT_DATA_TO,
    PUBLIC_OHLCV_APPROVAL_PHRASE,
    _gap_days,
    _load_json,
)
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan
from invis_alpha_os.reports.manual_csv_schema import CANONICAL_COLUMNS
from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file
from invis_alpha_os.reports.manual_data_discovery import (
    discover_manual_data_candidates,
    probe_path_ohlcv_schema,
)
from invis_alpha_os.reports.manual_data_schema_guard import DEFAULT_TARGET_TICKERS_CSV

POST_CONTRACT_TICKERS_CSV = "5802,6645,285A,5803"
STRUCTURAL_FOCUS_TICKERS_CSV = "285A,5802,5803"
MANUAL_IMPORT_APPROVAL_PHRASE = "manual JP bars actual importを実行してよい"
DROPZONE_RELATIVE = "Downloads/invest-alpha-os-manual-data-dropzone/manual_jp_bars.csv"

_THEME_LABELS: dict[str, str] = {
    "memory": "半導体メモリ",
    "semiconductors": "半導体",
    "ai_infra": "AIインフラ",
    "energy": "電力・エネルギー",
    "automotive_wire": "自動車配線",
    "industrials": "産業資材",
    "communications": "通信",
    "cables": "ケーブル",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets(csv: str) -> list[str]:
    return [p.strip() for p in csv.split(",") if p.strip()]


def _theme_display(theme_csv: str) -> str:
    parts = [p.strip() for p in theme_csv.split(",") if p.strip()]
    labels = [_THEME_LABELS.get(p, p) for p in parts]
    return " / ".join(labels) if labels else "未分類"


def _candidate_by_ticker(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in context.get("candidates") or []:
        if isinstance(row, dict):
            t = str(row.get("ticker", "")).strip()
            if t:
                out[t] = row
    return out


def _select_best_discovery_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    safe = [c for c in candidates if c.get("safe_to_parse")]
    if not safe:
        return None
    return safe[0]


def _assess_csv_candidate(
    *,
    path: Path,
    targets_csv: str,
    report_date: str,
    contract_to: str,
) -> dict[str, Any]:
    schema_ok, schema_reason = probe_path_ohlcv_schema(path)
    validation = validate_manual_csv_file(
        csv_path=path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    plan = build_manual_csv_import_plan(
        csv_path=path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    date_max = validation.json_payload.get("date_max")
    post_contract = bool(
        date_max and isinstance(date_max, str) and date_max > contract_to
    )
    per_ticker_post: dict[str, bool] = {}
    for row in plan.json_payload.get("per_ticker") or []:
        if not isinstance(row, dict):
            continue
        t = str(row.get("ticker", ""))
        dm = row.get("date_max")
        per_ticker_post[t] = bool(dm and str(dm) > contract_to)
    return {
        "filename": path.name,
        "location_label": path.parent.name,
        "schema_ok": schema_ok,
        "schema_reason": schema_reason,
        "validated": validation.json_payload.get("validated"),
        "date_min": validation.json_payload.get("date_min"),
        "date_max": date_max,
        "row_count": validation.json_payload.get("row_count"),
        "post_contract_rows_present": post_contract,
        "per_ticker_post_contract": per_ticker_post,
        "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
        "importable_dry_run": plan.json_payload.get("importable"),
        "dry_run_only": True,
        "raw_contents_printed": False,
    }


def discover_post_contract_ohlcv(
    *,
    repo_root: Path,
    report_date: str,
    targets_csv: str = POST_CONTRACT_TICKERS_CSV,
    contract_to: str = CONTRACT_DATA_TO,
) -> dict[str, Any]:
    candidates = discover_manual_data_candidates(repo_root=repo_root)
    public_candidates = [
        {k: v for k, v in row.items() if k != "resolved_path"}
        for row in candidates
    ]
    selected = _select_best_discovery_candidate(candidates)
    assessment: dict[str, Any] | None = None
    if selected and selected.get("resolved_path"):
        path = Path(str(selected["resolved_path"]))
        if path.is_file():
            assessment = _assess_csv_candidate(
                path=path,
                targets_csv=targets_csv,
                report_date=report_date,
                contract_to=contract_to,
            )
    any_post = bool(assessment and assessment.get("post_contract_rows_present"))
    return {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v32",
        "contract_data_available_to": contract_to,
        "targets": _parse_targets(targets_csv),
        "candidates_found": len(public_candidates),
        "candidates": public_candidates,
        "selected_candidate": (
            {k: v for k, v in selected.items() if k != "resolved_path"} if selected else None
        ),
        "selected_assessment": assessment,
        "post_contract_ohlcv_found": any_post,
        "discovery_verdict": (
            "post_contract_candidate_ready_for_import_approval"
            if any_post
            else "no_post_contract_rows_use_manual_export"
        ),
        "secrets_printed": False,
        "raw_contents_printed": False,
    }


def build_post_contract_ohlcv_export_quick_guide(
    *,
    report_date: str,
    discovery: dict[str, Any],
    targets_csv: str = POST_CONTRACT_TICKERS_CSV,
) -> tuple[str, dict[str, Any]]:
    targets = _parse_targets(targets_csv)
    need_from = CONTRACT_DATA_TO
    need_to = report_date
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v32",
        "required_tickers": targets,
        "required_period": {
            "from_exclusive": need_from,
            "through_inclusive": need_to,
            "note": f"{need_from}より後の日次バーを{need_to}まで",
        },
        "required_columns": list(CANONICAL_COLUMNS),
        "prohibited_columns": [
            "account",
            "口座",
            "氏名",
            "取引",
            "約定",
            "評価額",
            "損益",
        ],
        "save_path_relative": DROPZONE_RELATIVE,
        "preferred_filename": "manual_jp_bars.csv",
        "recommended_source": "yahoo_finance_jp_manual_export",
        "single_user_action": (
            "Yahoo Finance JPで5802/6645/285A/5803の日足を"
            f"{need_from}翌営業日以降〜{need_to}までOHLCVのみCSV出力し、"
            f"~/Downloads/invest-alpha-os-manual-data-dropzone/manual_jp_bars.csv に上書き保存"
        ),
        "cursor_next_phrase": (
            "manual_jp_bars.csvをdropzoneに置いた。schema validationとdry-runを実行して"
        ),
        "discovery_verdict": discovery.get("discovery_verdict"),
        "post_contract_ohlcv_found": discovery.get("post_contract_ohlcv_found"),
        "secrets_printed": False,
    }
    md = "\n".join(
        [
            "# Post-Contract OHLCV Export Quick Guide",
            "",
            f"- report_date: {report_date}",
            f"- contract cap (cache): {CONTRACT_DATA_TO}",
            f"- need period: after {need_from} through {need_to}",
            f"- targets: {', '.join(targets)}",
            "",
            "## Required columns",
            "",
            f"- {', '.join(CANONICAL_COLUMNS)}",
            "",
            "## Save location",
            "",
            f"- `~/{DROPZONE_RELATIVE}`",
            "",
            "## One action for you",
            "",
            f"- {payload['single_user_action']}",
            "",
            "## Next phrase for Cursor",
            "",
            f"- `{payload['cursor_next_phrase']}`",
            "",
        ]
    )
    return md, payload


def build_alternative_ohlcv_manual_export_package_v32(
    *,
    report_date: str,
    discovery: dict[str, Any],
    targets_csv: str = POST_CONTRACT_TICKERS_CSV,
) -> tuple[str, dict[str, Any]]:
    targets = _parse_targets(targets_csv)
    assessment = discovery.get("selected_assessment") or {}
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v32",
        "package_status": (
            "awaiting_post_contract_export"
            if not discovery.get("post_contract_ohlcv_found")
            else "ready_for_import_dry_run"
        ),
        "recommended_source": "yahoo_finance_jp_manual_export",
        "target_tickers": targets,
        "required_columns": list(CANONICAL_COLUMNS),
        "dropzone_filename": "manual_jp_bars.csv",
        "existing_dropzone_date_max": assessment.get("date_max"),
        "rows_newer_than_cache_total": assessment.get("rows_newer_than_cache_total", 0),
        "exact_next_commands": [
            "weekly-candidate-brief-post-contract-ohlcv-structural-v32 --report-date "
            + report_date,
            "weekly-candidate-brief-manual-data-import-flow --input-path <dropzone>/manual_jp_bars.csv",
        ],
        "requires_user_approval_for_import": MANUAL_IMPORT_APPROVAL_PHRASE,
        "live_http_required": False,
        "cache_write_executed": False,
        "actual_import_executed": False,
        "secrets_printed": False,
    }
    md = "\n".join(
        [
            "# Alternative OHLCV Manual Export Package",
            "",
            f"- status: {payload['package_status']}",
            f"- source: {payload['recommended_source']}",
            f"- targets: {', '.join(targets)}",
            f"- dropzone latest date_max: {assessment.get('date_max', 'n/a')}",
            f"- rows_newer_than_cache: {payload['rows_newer_than_cache_total']}",
            "",
            "## Approval phrase (import only)",
            "",
            f"- `{MANUAL_IMPORT_APPROVAL_PHRASE}`",
            "",
        ]
    )
    return md, payload


def _watch_priority_for_candidate(
    *,
    ticker: str,
    candidate: dict[str, Any],
    trap: dict[str, Any],
    gap: int | None,
) -> tuple[str, str]:
    timing = str(candidate.get("timing", ""))
    classification = str(candidate.get("classification", ""))
    overheat = str((trap.get("overheat_risk") or {}).get("level", ""))
    dist75 = (candidate.get("moving_averages") or {}).get("dist_ma75_pct")
    if gap is not None and gap >= 60:
        if classification == "top_pick" and timing == "wait_for_pullback":
            return "watch_high", "テーマ上位・押し目待ちだが84日ギャップで価格未確定"
        if timing in {"overheated_watch", "monitor"}:
            return "watch_high", "ブレイクアウト監視テーマだがPost-2026-03 OHLCV必須"
        return "watch_medium", "構造分析のみ可・タイミングはデータ後"
    if overheat == "高":
        return "watch_high", "過熱リスク高・無効化条件の監視優先"
    if isinstance(dist75, (int, float)) and dist75 > 0.3:
        return "watch_medium", "75日線上乖離大・調整監視"
    return "watch_low", "優先度低またはデータ不足"


def _structural_row(
    *,
    ticker: str,
    candidate: dict[str, Any],
    trap: dict[str, Any],
    report_date: str,
) -> dict[str, Any]:
    latest = str(candidate.get("latest_bar_date") or CONTRACT_DATA_TO)
    gap = _gap_days(report_date, latest)
    theme_raw = str(candidate.get("theme", ""))
    watch_pri, watch_reason = _watch_priority_for_candidate(
        ticker=ticker, candidate=candidate, trap=trap, gap=gap
    )
    ma = candidate.get("moving_averages") or {}
    dist75 = ma.get("dist_ma75_pct")
    invalidation = list(trap.get("invalidation_conditions") or [])[:3]
    upside = list(trap.get("upside_thesis") or [])[:2]
    downside = list(trap.get("downside_thesis") or [])[:2]
    post_ohlcv_triggers = [
        f"Post-{CONTRACT_DATA_TO}で75日線維持/割れを確認",
        "出来高伴う高値更新 or 失速",
        "テーマニュースと需給の整合",
    ]
    return {
        "ticker": ticker,
        "name": candidate.get("name", ticker),
        "theme": _theme_display(theme_raw),
        "theme_tags": theme_raw,
        "watch_priority": watch_pri,
        "watch_priority_reason": watch_reason,
        "confidence": "低" if gap and gap >= 60 else "中",
        "timing_label": candidate.get("timing_label_ja") or candidate.get("timing"),
        "data_gap_note": (
            f"latest={latest}; gap={gap}日; "
            "Post-2026-03価格なしのため売買タイミング断定不可"
        ),
        "theme_fit_summary": _theme_fit_summary(theme_raw, ticker),
        "overheat_trap_risk": (trap.get("overheat_risk") or {}).get("level"),
        "value_trap_risk": (trap.get("value_trap_risk") or {}).get("level"),
        "dist_ma75_pct": dist75,
        "invalidation": invalidation,
        "upside_trigger": upside,
        "downside_trigger": downside,
        "post_ohlcv_review_triggers": post_ohlcv_triggers,
        "uncertain_until_ohlcv": [
            "直近高値/安値の更新",
            "ブレイクアウト vs ダマシ",
            "押し目の深さと出来高",
        ],
    }


def _theme_fit_summary(theme_raw: str, ticker: str) -> str:
    tags = {p.strip() for p in theme_raw.split(",")}
    if "memory" in tags or "semiconductors" in tags:
        return "AI/datacenter投資→メモリ需給サイクルに連動。急伸後はtrap/overheatを優先監視。"
    if "cables" in tags or "ai_infra" in tags:
        return "AIインフラ/光・ケーブル需要テーマ。同業比較と受注トレンドが鍵。"
    if "energy" in tags:
        return "電力・エネルギー/素材コストと配線・電力ケーブル需要。銅価・受注が観測軸。"
    return f"{ticker}: テーマタグに基づく構造監視（価格タイミングはOHLCV更新後）"


def build_structural_theme_deep_dive(
    *,
    report_date: str,
    reports_latest_dir: Path,
    focus_csv: str = STRUCTURAL_FOCUS_TICKERS_CSV,
) -> tuple[str, dict[str, Any]]:
    context = _load_json(reports_latest_dir / "chatgpt_invest_context_pack.json")
    candidates = _candidate_by_ticker(context)
    rows: list[dict[str, Any]] = []
    for ticker in _parse_targets(focus_csv):
        cand = candidates.get(ticker)
        if not cand:
            continue
        trap = analyze_candidate_traps(cand)
        rows.append(
            _structural_row(
                ticker=ticker, candidate=cand, trap=trap, report_date=report_date
            )
        )
    for extra in ("6645", "5801"):
        cand = candidates.get(extra)
        if cand:
            trap = analyze_candidate_traps(cand)
            rows.append(
                _structural_row(
                    ticker=extra, candidate=cand, trap=trap, report_date=report_date
                )
            )
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v32",
        "disclaimer": "投資助言ではなく監視・テーマ整理。84日ギャップ下ではタイミング断定不可。",
        "contract_data_available_to": CONTRACT_DATA_TO,
        "per_ticker": rows,
        "secrets_printed": False,
    }
    lines = [
        "# Structural Theme Deep Dive After Refresh",
        "",
        payload["disclaimer"],
        "",
        "| ticker | theme | watch_priority | confidence | data_gap_note |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        note = str(r["data_gap_note"])
        if len(note) > 56:
            note = note[:53] + "..."
        lines.append(
            f"| {r['ticker']} | {r['theme']} | {r['watch_priority']} | "
            f"{r['confidence']} | {note} |"
        )
    return "\n".join(lines), payload


def build_candidate_watch_priority(
    structural_json: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    rows = structural_json.get("per_ticker") or []
    ordered = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: {
            "watch_high": 0,
            "watch_medium": 1,
            "watch_low": 2,
            "defer": 3,
        }.get(str(r.get("watch_priority")), 9),
    )
    triggers: list[dict[str, Any]] = []
    for r in ordered:
        triggers.append(
            {
                "ticker": r.get("ticker"),
                "upside_trigger": r.get("upside_trigger"),
                "downside_trigger": r.get("downside_trigger"),
                "invalidation": r.get("invalidation"),
                "post_ohlcv_review_triggers": r.get("post_ohlcv_review_triggers"),
            }
        )
    payload: dict[str, Any] = {
        "report_date": structural_json.get("report_date"),
        "generated_at": _now_iso(),
        "pack_version": "v32",
        "priority_order": [r.get("ticker") for r in ordered],
        "per_ticker": [
            {
                "ticker": r.get("ticker"),
                "watch_priority": r.get("watch_priority"),
                "watch_priority_reason": r.get("watch_priority_reason"),
            }
            for r in ordered
        ],
        "key_watch_triggers": triggers,
        "secrets_printed": False,
    }
    lines = [
        "# Candidate Watch Priority After Refresh",
        "",
        "## Priority order",
        "",
        f"- {' > '.join(payload['priority_order'])}",
        "",
        "| ticker | watch_priority | reason |",
        "|---|---|---|",
    ]
    for r in ordered:
        reason = str(r.get("watch_priority_reason", ""))
        if len(reason) > 64:
            reason = reason[:61] + "..."
        lines.append(
            f"| {r.get('ticker')} | {r.get('watch_priority')} | {reason} |"
        )
    lines.extend(
        [
            "",
            "## Key watch triggers",
            "",
            "| ticker | upside | downside | invalidation |",
            "|---|---|---|---|",
        ]
    )
    for t in triggers:
        up = "; ".join(t.get("upside_trigger") or [])[:48]
        down = "; ".join(t.get("downside_trigger") or [])[:48]
        inv = "; ".join(t.get("invalidation") or [])[:48]
        lines.append(f"| {t.get('ticker')} | {up} | {down} | {inv} |")
    return "\n".join(lines), payload


def _ohlcv_need_rows(report_date: str) -> list[dict[str, Any]]:
    targets = _parse_targets(DEFAULT_TARGET_TICKERS_CSV)
    rows: list[dict[str, Any]] = []
    for ticker in targets:
        need = "must_have_recent_ohlcv" if ticker in {"5802", "6645", "285A", "5803"} else "defer"
        if ticker == "5801":
            need = "defer"
        rows.append(
            {
                "ticker": ticker,
                "need_level": need,
                "required_period": f"after {CONTRACT_DATA_TO} through {report_date}",
                "reason": (
                    "momentum/breakout/timingにPost-2026-03必須"
                    if need == "must_have_recent_ohlcv"
                    else "v31で見送り・優先度低"
                ),
            }
        )
    return rows


@dataclass(frozen=True)
class PostContractStructuralV32Result:
    discovery_json: dict[str, Any]
    discovery_markdown: str
    quick_guide_markdown: str
    quick_guide_json: dict[str, Any]
    alternative_export_markdown: str
    alternative_export_json: dict[str, Any]
    structural_markdown: str
    structural_json: dict[str, Any]
    watch_markdown: str
    watch_json: dict[str, Any]
    public_live_fetch_markdown: str
    public_live_fetch_json: dict[str, Any]
    ohlcv_need_markdown: str
    ohlcv_need_json: dict[str, Any]


def build_post_contract_structural_v32(
    *,
    report_date: str,
    repo_root: Path,
    reports_latest_dir: Path,
    targets_csv: str = POST_CONTRACT_TICKERS_CSV,
) -> PostContractStructuralV32Result:
    discovery = discover_post_contract_ohlcv(
        repo_root=repo_root,
        report_date=report_date,
        targets_csv=targets_csv,
    )
    q_md, q_json = build_post_contract_ohlcv_export_quick_guide(
        report_date=report_date, discovery=discovery, targets_csv=targets_csv
    )
    alt_md, alt_json = build_alternative_ohlcv_manual_export_package_v32(
        report_date=report_date, discovery=discovery, targets_csv=targets_csv
    )
    s_md, s_json = build_structural_theme_deep_dive(
        report_date=report_date, reports_latest_dir=reports_latest_dir
    )
    w_md, w_json = build_candidate_watch_priority(s_json)
    need_rows = _ohlcv_need_rows(report_date)
    need_json: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v32",
        "per_ticker": need_rows,
    }
    need_md_lines = [
        "# Post-2026-03 OHLCV Need Assessment (v32)",
        "",
        "| ticker | need_level | required_period | reason |",
        "|---|---|---|---|",
    ]
    for r in need_rows:
        need_md_lines.append(
            f"| {r['ticker']} | {r['need_level']} | {r['required_period']} | {r['reason']} |"
        )
    public_json = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "package_status": "deferred_not_primary",
        "required_approval_phrase": PUBLIC_OHLCV_APPROVAL_PHRASE,
        "note": "Post-contract gap; manual Yahoo export is primary",
        "live_http_required": True,
        "cache_write_required": True,
    }
    disc_md = "\n".join(
        [
            "# Post-Contract OHLCV Discovery",
            "",
            f"- verdict: {discovery.get('discovery_verdict')}",
            f"- post_contract_found: {discovery.get('post_contract_ohlcv_found')}",
            f"- candidates_found: {discovery.get('candidates_found')}",
            "",
        ]
    )
    if discovery.get("selected_assessment"):
        a = discovery["selected_assessment"]
        disc_md += (
            f"- selected: {a.get('filename')} @ {a.get('location_label')}\n"
            f"- schema_ok: {a.get('schema_ok')}\n"
            f"- date_max: {a.get('date_max')}\n"
            f"- rows_newer_than_cache: {a.get('rows_newer_than_cache_total')}\n"
        )
    return PostContractStructuralV32Result(
        discovery_json=discovery,
        discovery_markdown=disc_md,
        quick_guide_markdown=q_md,
        quick_guide_json=q_json,
        alternative_export_markdown=alt_md,
        alternative_export_json=alt_json,
        structural_markdown=s_md,
        structural_json=s_json,
        watch_markdown=w_md,
        watch_json=w_json,
        public_live_fetch_markdown="# Public OHLCV Live Fetch Approval Package\n\n"
        f"- phrase: {PUBLIC_OHLCV_APPROVAL_PHRASE}\n",
        public_live_fetch_json=public_json,
        ohlcv_need_markdown="\n".join(need_md_lines),
        ohlcv_need_json=need_json,
    )


def write_post_contract_structural_v32_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: PostContractStructuralV32Result,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    pairs = [
        ("post_contract_ohlcv_discovery", result.discovery_markdown, result.discovery_json),
        ("post_contract_ohlcv_export_quick_guide", result.quick_guide_markdown, result.quick_guide_json),
        ("alternative_ohlcv_manual_export_package", result.alternative_export_markdown, result.alternative_export_json),
        ("structural_theme_deep_dive_after_refresh", result.structural_markdown, result.structural_json),
        ("candidate_watch_priority_after_refresh", result.watch_markdown, result.watch_json),
        ("public_ohlcv_live_fetch_approval_package", result.public_live_fetch_markdown, result.public_live_fetch_json),
        ("post_2026_03_ohlcv_need_assessment", result.ohlcv_need_markdown, result.ohlcv_need_json),
    ]
    for stem, md, js in pairs:
        for root in (latest, weekly):
            mp = root / f"{stem}.md"
            jp = root / f"{stem}.json"
            mp.write_text(md, encoding="utf-8")
            jp.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"latest_{stem}_md"] = latest / f"{stem}.md"
        paths[f"latest_{stem}_json"] = latest / f"{stem}.json"
    return paths


def sync_post_contract_structural_v32_to_reports_repo(
    *,
    reports_repo_path: Path,
    report_date: str,
    result: PostContractStructuralV32Result,
) -> dict[str, Path]:
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    pairs = [
        ("post_contract_ohlcv_export_quick_guide", result.quick_guide_markdown, result.quick_guide_json),
        ("alternative_ohlcv_manual_export_package", result.alternative_export_markdown, result.alternative_export_json),
        ("structural_theme_deep_dive_after_refresh", result.structural_markdown, result.structural_json),
        ("candidate_watch_priority_after_refresh", result.watch_markdown, result.watch_json),
        ("post_2026_03_ohlcv_need_assessment", result.ohlcv_need_markdown, result.ohlcv_need_json),
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
