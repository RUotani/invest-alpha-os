"""Weekly Candidate Brief v0.1 — cross-market discovery as primary weekly output (observation-only)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Literal, Sequence

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.config.paths import CONFIG_DIR, ROOT_DIR
from invis_alpha_os.discovery.cross_market_contract import (
    DISCOVERY_SCORE_DISCLAIMER,
    MARKET_JP,
    MARKET_US,
    OBSERVATION_DISCLAIMER,
    assert_no_forbidden_terms,
    format_pct,
    jp_candidate_to_common,
    merge_cross_market_json_payloads,
    us_candidate_to_common,
)
from invis_alpha_os.discovery.jp_universe_scanner import (
    JpDiscoveryScanResult,
    format_jp_discovery_json,
    scan_jp_universe,
)
from invis_alpha_os.discovery.us_universe_scanner import (
    UsDiscoveryScanResult,
    format_us_discovery_json,
    scan_us_universe,
)

from invis_alpha_os.portfolio.target_allocation_gap_calculator_v82 import (
    compute_target_allocation_gap_from_portfolio_context_v82,
    format_target_allocation_gap_markdown_short_v82,
)
from invis_alpha_os.product.candidate_score_veto_pipeline_v93 import (
    CandidateIntegratedAssessment,
    build_fixture_integrated_candidate_assessments_v93,
    render_integrated_candidate_assessment_markdown,
    render_integrated_candidate_assessment_summary_lines,
)
from invis_alpha_os.product.monthly_input_consistency_v95 import (
    build_redacted_monthly_portfolio_fixture_v95,
    render_monthly_input_consistency_summary_lines_v95,
    validate_monthly_portfolio_input_v95,
)
from invis_alpha_os.product.sanitized_manual_input_report_connection_v99 import (
    build_sanitized_manual_input_summary_lines_v99,
)
from invis_alpha_os.product.weekly_candidate_pipeline_trace_v90 import (
    CandidatePipelineTraceSummary,
    CandidateTraceInput,
    build_candidate_pipeline_trace_summary,
)
from invis_alpha_os.product.weekly_email_shared_view_model_v96 import (
    build_weekly_shared_view_model_v96,
    render_weekly_shared_view_model_markdown_v96,
)
from invis_alpha_os.signals.coverage_reason_taxonomy_v112 import (
    parse_coverage_reason_codes_from_english,
    translate_user_facing_coverage_reason_to_ja,
)

CandidateBriefType = Literal[
    "top_pick",
    "rapid_mover",
    "pullback",
    "theme",
    "avoid",
    "insufficient",
]

TOP_PICK_COUNT = 5
SECTION_TOP_COUNT = 3

PULLBACK_R60_MIN = 0.05
PULLBACK_R20_MIN = 0.0
PULLBACK_R5_MAX = -0.02
PULLBACK_R5_MIN = -0.12

# ETF proxy candidates (US observation-only). These are used both for:
# - macro environment overview
# - Top5 diversification coverage constraints
ETF_PROXY_SYMBOLS: tuple[str, ...] = ("SPY", "QQQ", "TLT", "TMF", "GLDM", "SLV")

# Backward-compatible alias (used by macro summary builder).
MACRO_PROXY_SYMBOLS: tuple[str, ...] = ETF_PROXY_SYMBOLS

BRIEF_DISCLAIMER_JA = (
    "観測のみ — 売買推奨・自動売買・注文は行いません。"
    " discovery_score はリサーチ優先度の目安です。"
)

PORTFOLIO_CONTEXT_V81: dict[str, str] = {
    "source": "2026-05 month-end redacted portfolio context",
    "total_assets": "約4,327.9万円",
    "cash": "508.2万円 / 11.7%",
    "equity_total": "2,934.5万円 / 67.8%",
    "individual_stocks": "846.3万円 / 19.6%",
    "bonds": "582.7万円 / 13.5%",
    "gold": "234.5万円 / 5.4%",
    "crypto_high_beta": "57.5万円 / 1.3%",
    "leverage": "10.5万円 / 0.2%",
    "cash_policy": "現金比率は最低15%、できれば20%方向へ戻す",
    "individual_policy": "個別株は徐々に10〜15%方向へ圧縮",
}

PORTFOLIO_ACTION_BIAS_V81 = (
    "現金比率が11.7%で最低目安15%を下回るため、強い根拠のない新規リスク追加よりも、"
    "監視・整理・現金回復を優先します。"
)

_TARGET_ALLOCATION_GAP_V82 = compute_target_allocation_gap_from_portfolio_context_v82(PORTFOLIO_CONTEXT_V81)

DO_ITEMS_V81: tuple[str, ...] = (
    "候補0件の理由とcoverage不足を確認する",
    "現金比率が低い前提で、新規リスク追加を抑制する",
    "整理候補・高ボラ枠を次回レビュー対象にする",
)

DONT_ITEMS_V81: tuple[str, ...] = (
    "候補0件を「問題なし」と解釈しない",
    "データ不足のまま個別株リスクを増やさない",
    "高ボラ/レバ商品を雰囲気で追いかけない",
)

ALLOWED_ACTION_ITEMS_V85: tuple[str, ...] = (
    "候補0件の理由、coverage不足、score未達、veto理由を確認する",
    "新規リスク追加ではなく、監視候補・整理候補・高ボラ枠の根拠確認を進める",
    "現金11.7%から最低15%、できれば20%方向へ戻す前提で、週次判断を記録する",
)

SUPPRESSED_ACTION_ITEMS_V85: tuple[str, ...] = (
    "現金比率11.7%のまま、根拠不足の新規個別株・高ベータ枠を追加しない",
    "個別株19.6%が10〜15%目安を上回る前提で、個別株候補を強い新規リスク候補扱いしない",
    "データ不足候補を、coverage・価格・score内訳を確認しないまま深掘り対象にしない",
)

NEXT_CHECK_ITEMS_V85: tuple[str, ...] = (
    "現金比率が15%未満で止まっていないか、20%回復ゾーンへ向かう余地があるか",
    "株式系67.8%と個別株19.6%に重複リスク・高ボラ偏り・整理候補がないか",
    "次回weekly runで候補0件の理由が、データ不足から条件未達へ改善しているか",
)

CLEANUP_PRIORITY_NOTE_V83 = "このスコアは売却指示ではなく、次に確認すべき整理・監視優先度です。"

CLEANUP_SCORE_SCALE_V83: tuple[str, ...] = (
    "0: 今週は対象外",
    "1: 低い監視",
    "2: 軽い確認",
    "3: 要確認",
    "4: 高優先で監視・整理検討",
    "5: 強い抑制・新規追加禁止寄り",
)
PIPELINE_SCORE_THRESHOLD_V90 = 1.0


@dataclass(frozen=True)
class UnifiedCandidate:
    market: str
    instrument_id: str
    display_name: str
    discovery_score: int
    latest_date: str
    close: float | None
    return_5d: float | None
    return_20d: float | None
    return_60d: float | None
    labels: tuple[str, ...]
    categories: tuple[str, ...]
    data_quality: str
    reason: str
    themes: tuple[str, ...] = ()
    volume_status: str | None = None
    volume_ratio_25d: float | None = None
    high_distance_pct: float | None = None


@dataclass(frozen=True)
class CandidateCard:
    brief_type: CandidateBriefType
    candidate: UnifiedCandidate
    reason: str
    counter_evidence: tuple[str, ...]
    next_checks: tuple[str, ...]


@dataclass(frozen=True)
class CleanupPriorityRow:
    target: str
    classification: str
    priority: int
    cash_pressure: int
    allocation_excess: int
    evidence_gap: int
    volatility_risk: int
    duplication_risk: int
    main_reason: str
    weekly_treatment: str


@dataclass
class WeeklyCandidateBriefV0:
    report_date: str
    generated_at_jp: str
    generated_at_us: str
    jp_scope: str
    us_scope: str
    macro_summary: str
    top_picks: list[CandidateCard] = field(default_factory=list)
    rapid_movers: list[CandidateCard] = field(default_factory=list)
    pullbacks: list[CandidateCard] = field(default_factory=list)
    avoid_list: list[CandidateCard] = field(default_factory=list)
    insufficient_list: list[CandidateCard] = field(default_factory=list)
    theme_highlights: list[CandidateCard] = field(default_factory=list)
    appendix_lines: tuple[str, ...] = ()
    coverage_note: str | None = None
    discovery_merge: dict[str, Any] = field(default_factory=dict)
    pipeline_trace: CandidatePipelineTraceSummary | None = None
    score_veto_assessments: tuple[CandidateIntegratedAssessment, ...] = field(default_factory=tuple)


def _sort_key(c: UnifiedCandidate) -> tuple[int, float, str]:
    r20 = float(c.return_20d) if c.return_20d is not None else -1e18
    return (-c.discovery_score, -r20, c.instrument_id)


def _from_common(row: dict[str, Any], *, themes: tuple[str, ...] = ()) -> UnifiedCandidate:
    return UnifiedCandidate(
        market=str(row["market"]),
        instrument_id=str(row["instrument_id"]),
        display_name=str(row["display_name"]),
        discovery_score=int(row.get("discovery_score") or 0),
        latest_date=str(row.get("latest_date") or ""),
        close=row.get("close"),
        return_5d=row.get("return_5d"),
        return_20d=row.get("return_20d"),
        return_60d=row.get("return_60d"),
        labels=tuple(str(x) for x in (row.get("labels") or [])),
        categories=tuple(str(x) for x in (row.get("categories") or [])),
        data_quality=str(row.get("data_quality") or ""),
        reason=str(row.get("reason") or ""),
        themes=themes,
        volume_status=row.get("volume_status"),
        volume_ratio_25d=row.get("volume_ratio_25d"),
        high_distance_pct=row.get("high_distance_pct"),
    )


def _jp_rows(result: JpDiscoveryScanResult, theme_map: dict[str, tuple[str, ...]]) -> tuple[list[UnifiedCandidate], list[UnifiedCandidate]]:
    ranked = [
        _from_common(jp_candidate_to_common(c), themes=theme_map.get(c.code, ()))
        for c in result.candidates
    ]
    insufficient = [
        _from_common(jp_candidate_to_common(c), themes=theme_map.get(c.code, ()))
        for c in result.insufficient
    ]
    return ranked, insufficient


def _us_rows(result: UsDiscoveryScanResult, theme_map: dict[str, tuple[str, ...]]) -> tuple[list[UnifiedCandidate], list[UnifiedCandidate]]:
    ranked = [
        _from_common(us_candidate_to_common(c), themes=theme_map.get(c.symbol, ()))
        for c in result.candidates
    ]
    insufficient = [
        _from_common(us_candidate_to_common(c), themes=theme_map.get(c.symbol, ()))
        for c in result.insufficient
    ]
    return ranked, insufficient


def load_jp_theme_map(*, config_dir: Path | None = None) -> dict[str, tuple[str, ...]]:
    path = (config_dir or CONFIG_DIR) / "watchlist.yaml"
    if not path.is_file():
        return {}
    data = load_yaml(path)
    out: dict[str, tuple[str, ...]] = {}
    for item in data.get("jp_watchlist") or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("ticker") or item.get("code") or "").strip().upper()
        if not code:
            continue
        themes = tuple(str(t).strip() for t in (item.get("themes") or []) if str(t).strip())
        out[code] = themes
    return out


def load_us_theme_map(*, config_dir: Path | None = None) -> dict[str, tuple[str, ...]]:
    path = (config_dir or CONFIG_DIR) / "us_watchlist.yaml"
    if not path.is_file():
        return {}
    data = load_yaml(path)
    out: dict[str, tuple[str, ...]] = {}
    section_themes: tuple[tuple[str, str], ...] = (
        ("us_equities", "us_equity"),
        ("us_etfs", "us_etf"),
        ("crypto_proxy", "crypto_proxy"),
    )
    for section, theme in section_themes:
        raw = data.get(section) or []
        if not isinstance(raw, list):
            continue
        for sym in raw:
            sym_u = str(sym).strip().upper()
            if sym_u:
                out[sym_u] = (theme,)
    return out


def is_pullback_candidate(c: UnifiedCandidate) -> bool:
    if "overheated_caution" in c.categories:
        return False
    if c.data_quality != "ok":
        return False
    r5, r20, r60 = c.return_5d, c.return_20d, c.return_60d
    if r60 is None or r20 is None or r5 is None:
        return False
    return (
        r60 >= PULLBACK_R60_MIN
        and r20 >= PULLBACK_R20_MIN
        and PULLBACK_R5_MIN <= r5 <= PULLBACK_R5_MAX
    )


def is_avoid_candidate(c: UnifiedCandidate) -> bool:
    if "overheated_caution" in c.categories:
        return True
    if "low_liquidity_caution" in c.labels:
        return True
    if c.volume_status in ("low", "high") and "overheat_caution" in c.labels:
        return True
    return False


CandidateGroup = Literal["jp", "us_equity", "etf_proxy", "other_us"]


def candidate_group(c: UnifiedCandidate) -> CandidateGroup:
    if c.market == MARKET_JP:
        return "jp"
    if c.market == MARKET_US:
        if c.instrument_id in ETF_PROXY_SYMBOLS or "us_etf" in c.themes:
            return "etf_proxy"
        if "us_equity" in c.themes:
            return "us_equity"
        return "other_us"
    return "other_us"


def select_diversified_top_picks(
    *,
    jp_ranked: Sequence[UnifiedCandidate],
    us_ranked: Sequence[UnifiedCandidate],
    all_ranked: Sequence[UnifiedCandidate],
) -> tuple[list[CandidateCard], str | None]:
    """Select Top-N with JP / US equity / ETF proxy coverage constraints.

    Coverage rule:
    - If candidates exist, Top5 should include at least one JP, one US equity, and one ETF proxy.
    - If a group is empty, emit coverage_note for the missing reason (score-based exclusion is NOT assumed).
    """

    # all_ranked is already sorted by discovery_score (descending) by _sort_key upstream.
    by_group: dict[CandidateGroup, list[UnifiedCandidate]] = {
        "jp": [],
        "us_equity": [],
        "etf_proxy": [],
        "other_us": [],
    }
    for c in all_ranked:
        by_group[candidate_group(c)].append(c)

    desired_groups: tuple[CandidateGroup, ...] = ("jp", "us_equity", "etf_proxy")
    available = {g: len(by_group[g]) > 0 for g in desired_groups}

    selected: list[UnifiedCandidate] = []
    selected_ids: set[str] = set()

    def _take_best(g: CandidateGroup) -> None:
        if not by_group[g]:
            return
        c0 = by_group[g][0]
        key = f"{c0.market}:{c0.instrument_id}"
        if key in selected_ids:
            return
        selected.append(c0)
        selected_ids.add(key)

    # First, force coverage by taking the best from each available group.
    for g in desired_groups:
        _take_best(g)

    # Then fill remaining slots with best candidates overall.
    for c in all_ranked:
        if len(selected) >= TOP_PICK_COUNT:
            break
        key = f"{c.market}:{c.instrument_id}"
        if key in selected_ids:
            continue
        selected.append(c)
        selected_ids.add(key)

    missing: list[str] = []
    for g in desired_groups:
        if not available[g]:
            if g == "jp":
                missing.append("JP candidates were unavailable due to insufficient JP cache quality")
            elif g == "us_equity":
                missing.append("US equity candidates were unavailable due to insufficient data quality")
            elif g == "etf_proxy":
                missing.append("ETF proxy candidates were unavailable due to insufficient data quality")

    coverage_note: str | None = None
    if missing:
        coverage_note = "coverage_note: " + " / ".join(missing)

    cards = [_make_card(c, "top_pick") for c in selected[:TOP_PICK_COUNT]]
    return cards, coverage_note


def build_counter_evidence(c: UnifiedCandidate) -> tuple[str, ...]:
    out: list[str] = []

    if "overheated_caution" in c.categories or "overheat_caution" in c.labels:
        out.append(
            "短期の過熱サイン: "
            f"20日 {format_pct(c.return_20d)} / 60日 {format_pct(c.return_60d)}。"
            " 急伸後の調整局面を警戒する。"
        )

    if "volume_spike" in c.labels:
        vr = c.volume_ratio_25d
        vr_s = f"{vr:.2f}x" if isinstance(vr, (int, float)) else "—"
        out.append(
            f"出来高スパイクの持続性が鍵: 25日平均との差比 {vr_s}。"
            " イベント一過性の可能性もあるため確認する。"
        )

    if "near_high" in c.labels:
        hd = c.high_distance_pct
        out.append(
            "高値近辺の反応: "
            f"高値からの距離 {format_pct(hd)}。"
            " セクター要因の上乗せだけなら反落リスクもある。"
        )

    if "low_liquidity_caution" in c.labels:
        out.append(
            "流動性注意: "
            "板の薄さ/スプレッドの拡大で短期の値動きが歪む可能性。"
        )

    if "insufficient_data" in c.categories:
        out.append(
            "データ不足: キャッシュ履歴が短い/欠損の可能性。"
            " ラベル由来の推論は過信しない。"
        )

    # Even when we only have pure momentum labels, keep the counter evidence
    # candidate-specific by referencing the observed return magnitude.
    if "rapid_mover_20d" in c.labels and len(out) < 2:
        out.append(
            "急伸局面の反転リスク: "
            f"20日 {format_pct(c.return_20d)} の強さに対し、利益確定/需要一服の確認が必要。"
        )
    if "rapid_mover_5d" in c.labels and len(out) < 2:
        out.append(
            "短期の勢いの持続性: "
            f"5日 {format_pct(c.return_5d)} が弱まると、上昇の見かけが剥落する可能性。"
        )

    if not out:
        out.append(
            "観測スコアだけでは因果が不明。"
            " 決算・需給・マクロで無効化条件を確認する。"
        )

    # Ensure at least one line; keep it short and candidate-specific.
    return tuple(out[:2])


def build_next_checks(c: UnifiedCandidate) -> tuple[str, ...]:
    def _dedupe(seq: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in seq:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    checks: list[str] = []

    if candidate_group(c) == "etf_proxy":
        if c.instrument_id in ("TLT", "TMF"):
            checks = [
                "金利・カーブ（実質金利 proxy）と株式リスクの同時変化",
                "インフレ指標と期待金利の整合",
                "SPY/QQQ との相関が崩れていないか",
            ]
        elif c.instrument_id in ("GLDM", "SLV"):
            checks = [
                "実質金利とドル（DXY proxy）との連動確認",
                "需給/供給ニュース（供給制約・在庫の変化）",
                "リスクオン/オフの指数 proxy との整合",
            ]
        else:  # SPY/QQQ (default)
            checks = [
                "指数内の広がり（breadth）とセクター回転の有無",
                "金利感応度とバリュエーション観点",
                "個別株の弱さが目立たないか（バンド内確認）",
            ]
    elif c.market == MARKET_US:
        # US equity deep-dive入口を、銘柄（またはテーマ）で変える
        ticker = c.instrument_id
        checks = [
            {
                "NVDA": "AI/半導体系の設備投資（capex）と需給サイクル",
                "MSFT": "クラウド/ソフトウェア需要とガイダンスの更新",
                "AAPL": "iPhone/サービス収益構造と為替感応度",
                "AMZN": "クラウド/広告の成長率とコスト構造",
                "GOOGL": "広告・クラウド投資の持続性と規制/競争要因",
                "META": "広告市況の回復度合いとユーザー指標の変化",
                "TSLA": "EV需要のトレンドと値付け/粗利の耐性",
            }.get(ticker, "直近ニュースとセクター相対（同業比較）"),
            {
                "NVDA": "半導体価格/リードタイムの変化（NAND/DRAM指標など）",
                "MSFT": "ストック/サブスクの解約率・成長率の確認",
                "AAPL": "製品ミックスとコストの期ズレ有無",
                "AMZN": "クラウドの営業利益率と回復タイミング",
                "GOOGL": "広告単価と検索/動画の伸びの整合",
                "META": "広告単価とエンゲージメントの変化",
                "TSLA": "需要/供給（納車・在庫）の整合",
            }.get(ticker, "バリュエーションとガイダンスの整合"),
            "流動性・スプレッド確認（特にボラ上昇時）",
        ]
    else:
        # JP themes deep-dive入口
        themes = set(c.themes or [])
        if c.instrument_id == "5803":
            # Fujikura-like: prioritize cable/communications/data-center demand (avoid NAND/DRAM-style checks).
            checks = [
                "光ファイバー/データセンター需要と発注サイクル",
                "電線・通信インフラ投資と需給（部材/納期）",
                "銅価格・素材コストの動きと利益率への波及",
            ]
        elif c.instrument_id == "7203":
            # Toyota-like: avoid industrial equipment mapping unless explicitly justified.
            checks = [
                "為替（円/ドル）と原材料コストの変化",
                "需要/販売台数と販売サイクル（回復タイミング）",
                "ハイブリッド/EV ミックスとガイダンス更新",
            ]
        elif "energy" in themes or "automotive_wire" in themes:
            checks = [
                "銅価格・電力/素材コストの動きと業績への波及",
                "受注残/利益率の変化（粗利の耐性）",
                "競合比較（同業の上方修正の有無）",
            ]
        elif "ai_infra" in themes or "semiconductors" in themes or "memory" in themes:
            checks = [
                "NAND/DRAMなどメモリ/半導体市況（需給・価格）",
                "データセンター投資サイクルと設備投資の持続性",
                "設備投資の競争環境（顧客/取引先の反応）",
            ]
        elif "factory_automation" in themes or "industrials" in themes:
            checks = [
                "設備投資サイクルと受注指標（回復のタイミング）",
                "コスト構造（原材料/為替）の説明が一貫しているか",
                "競合比較（利益率の相対）",
            ]
        elif "communications" in themes or "cables" in themes or "digital" in themes:
            checks = [
                "通信/ネットワーク投資と需給（発注の質）",
                "部材価格と価格転嫁の進捗",
                "同セクターでの相対強さ（指数内）",
            ]
        else:
            checks = [
                "直近の開示・ニュースとセクター背景",
                "決算・バリュエーション（テーマ持続性）",
                "既存保有・ウォッチリストとの重複",
            ]

    # Label-driven extra checks should actually appear in the final 3 items.
    # Since the base list already has 3 slots, we replace the last slot when extras exist.
    extras: list[str] = []
    if "volume_spike" in c.labels:
        extras.append("出来高スパイクが再現するか（イベント一過性か）")
    elif is_pullback_candidate(c):
        extras.append("押し目検証: 60日トレンド維持のまま5日調整か反転か")

    if "overheated_caution" in c.categories or "overheat_caution" in c.labels:
        extras.append("急伸後の調整局面か: 反落の前兆（出来高減/高値推移）")

    base = checks
    if extras:
        checks = base[:2] + extras
    else:
        checks = base

    return tuple(_dedupe(checks)[:3])


def build_reason_human(c: UnifiedCandidate, brief_type: CandidateBriefType) -> str:
    """Convert internal discovery labels into human-friendly one-line reasons."""

    # Type-aware prefix (still human-readable; no trading recommendation wording).
    prefix_by_type: dict[CandidateBriefType, str] = {
        "top_pick": "注目理由",
        "rapid_mover": "急騰の観測理由",
        "pullback": "押し目の観測理由",
        "theme": "テーマの観測理由",
        "avoid": "回避の観測理由",
        "insufficient": "要注意（データ不足）",
    }

    overheat = "overheated_caution" in c.categories or "overheat_caution" in c.labels
    liq = "low_liquidity_caution" in c.labels

    theme_phrase: str | None = None
    if c.themes:
        theme_map = {
            "energy": "電力・エネルギーインフラ",
            "automotive_wire": "自動車向け電装/配線",
            "ai_infra": "AIインフラ/データセンター",
            "semiconductors": "半導体（需給サイクル）",
            "memory": "メモリ（NAND/DRAM）",
            "factory_automation": "工場自動化（設備投資）",
            "industrials": "産業設備・受注サイクル",
            "communications": "通信インフラ",
            "cables": "ケーブル/配線材料",
            "digital": "デジタル投資（成長ドライバー）",
        }
        if c.instrument_id == "7203":
            # Toyota: avoid incorrect industrial equipment mapping unless explicitly justified.
            theme_phrase = "自動車・モビリティ（需要サイクル/為替感応度）"
        else:
            for t in c.themes:
                if t in theme_map:
                    theme_phrase = theme_map[t]
                    break

    horizon_parts: list[str] = []
    if "rapid_mover_20d" in c.labels:
        horizon_parts.append("20日モメンタムが強い")
    if "rapid_mover_5d" in c.labels:
        horizon_parts.append("短期でも勢いがある")
    if "near_high" in c.labels:
        horizon_parts.append("52週高値近辺での反応")
    if "volume_spike" in c.labels:
        horizon_parts.append("出来高スパイクを伴う")

    # ETF proxy reasons (macro context for human deep-dive).
    if candidate_group(c) == "etf_proxy":
        sym = c.instrument_id
        if sym in ("TLT", "TMF"):
            base = "長期金利（長債）proxyとして、金利環境の変化が観測されている"
        elif sym in ("GLDM", "SLV"):
            base = "金属proxyとして、実質金利やドル要因への反応が観測されている"
        else:  # SPY/QQQ
            base = "株式指数proxyとして、リスク姿勢（指数モメンタム）の変化が観測されている"

        pct20 = format_pct(c.return_20d)
        pct60 = format_pct(c.return_60d)
        caution = " 短期の過熱サインがあるため急伸後の調整も先に確認。" if overheat else ""
        return f"{base}（20日 {pct20} / 60日 {pct60}）。{caution}".replace("。。", "。")

    # Pullback type: explicitly describe the shape using pullback gate conditions.
    if brief_type == "pullback" and is_pullback_candidate(c):
        pct5 = format_pct(c.return_5d)
        return (
            f"60日トレンドを維持しつつ、5日で小さく調整（直近 5日 {pct5}）。"
            + ("過熱が強い場合は調整が長引く可能性を確認。" if overheat else "")
        )

    # Avoid type: keep it caution-focused.
    if brief_type == "avoid":
        parts: list[str] = []
        if overheat:
            parts.append(f"過熱（20日 {format_pct(c.return_20d)} / 60日 {format_pct(c.return_60d)}）")
        if liq:
            parts.append("流動性注意")
        if not parts:
            parts.append("無効化条件の検証が先")
        return " / ".join(parts) + "（深掘り前に反証軸を確認）。"

    # Default human reason (JP / US equity)
    if not horizon_parts:
        horizon_parts = ["価格モメンタムと出来高の観測からスクリーニングされた"]

    # Add a human theme hook if available.
    if theme_phrase:
        horizon_parts.append(f"テーマ背景: {theme_phrase}")

    if overheat:
        horizon_parts.append("短期過熱のため、急伸後の無効化条件も先に確認")
    if liq:
        horizon_parts.append("流動性には注意（深掘り時に板/出来高を確認）")

    reason = "・".join(horizon_parts)
    return f"{prefix_by_type[brief_type]}: {reason}。"


def _make_card(c: UnifiedCandidate, brief_type: CandidateBriefType) -> CandidateCard:
    return CandidateCard(
        brief_type=brief_type,
        candidate=c,
        reason=build_reason_human(c, brief_type),
        counter_evidence=build_counter_evidence(c),
        next_checks=build_next_checks(c),
    )


def _macro_summary(us_ranked: Sequence[UnifiedCandidate]) -> str:
    by_id = {c.instrument_id: c for c in us_ranked}
    parts: list[str] = []
    for sym in MACRO_PROXY_SYMBOLS:
        row = by_id.get(sym)
        if row is None:
            continue
        role = {
            "SPY": "株式リスク",
            "TLT": "金利・ドル",
            "GLDM": "金",
            "SLV": "銀",
        }.get(sym, sym)
        parts.append(
            f"{role}({sym}): 20日 {format_pct(row.return_20d)}, 60日 {format_pct(row.return_60d)}"
        )
    if not parts:
        return (
            "マクロ proxy データなし（SPY/TLT/GLDM/SLV の US キャッシュが未整備）。"
            " 週次候補は個別銘柄モメンタム中心で解釈すること。"
        )
    spy = by_id.get("SPY")
    tlt = by_id.get("TLT")
    tone = "レジーム: 要確認"
    if spy and tlt and spy.return_20d is not None and tlt.return_20d is not None:
        if spy.return_20d > 0 and tlt.return_20d < 0:
            tone = "レジーム proxy: リスクオン寄り（株↑・長債↓）"
        elif spy.return_20d < 0 and tlt.return_20d > 0:
            tone = "レジーム proxy: リスクオフ寄り（株↓・長債↑）"
        else:
            tone = "レジーム proxy: 混在（株・債券の20日が同方向でない）"
    return tone + " · " + " · ".join(parts)


def _theme_highlights(ranked: Sequence[UnifiedCandidate], *, max_themes: int = 8) -> list[CandidateCard]:
    best: dict[str, UnifiedCandidate] = {}
    for c in ranked:
        if not c.themes:
            continue
        for theme in c.themes:
            prev = best.get(theme)
            if prev is None or _sort_key(c) < _sort_key(prev):
                best[theme] = c
    themes_sorted = sorted(best.keys())[:max_themes]
    return [_make_card(best[t], "theme") for t in themes_sorted]


def _dedupe_cards_by_symbol(cards: Sequence[CandidateCard]) -> list[CandidateCard]:
    """Remove duplicate candidate symbols to avoid repeated theme highlights."""
    seen: set[str] = set()
    out: list[CandidateCard] = []
    for card in cards:
        sym = card.candidate.instrument_id
        if sym in seen:
            continue
        seen.add(sym)
        out.append(card)
    return out


def _build_pipeline_trace_summary(
    *,
    ranked: Sequence[UnifiedCandidate],
    insufficient: Sequence[UnifiedCandidate],
    avoid_candidates: Sequence[UnifiedCandidate],
) -> CandidatePipelineTraceSummary:
    by_key: dict[str, CandidateTraceInput] = {}
    insufficient_keys: set[str] = set()
    avoid_map: dict[str, tuple[str, ...]] = {}

    for c in insufficient:
        insufficient_keys.add(f"{c.market}:{c.instrument_id}")
    for c in avoid_candidates:
        key = f"{c.market}:{c.instrument_id}"
        reasons = tuple(
            sorted(
                {
                    x
                    for x in {*c.categories, *c.labels}
                    if ("caution" in x) or ("veto" in x)
                }
            )
        )
        if not reasons:
            reasons = ("generic_veto",)
        avoid_map[key] = reasons

    for c in [*ranked, *insufficient]:
        key = f"{c.market}:{c.instrument_id}"
        has_required_coverage = c.data_quality == "ok" and key not in insufficient_keys
        data_insufficient_reasons = ("insufficient_data",) if key in insufficient_keys else ()
        veto_reasons = avoid_map.get(key, ())
        by_key[key] = CandidateTraceInput(
            symbol=c.instrument_id,
            name=c.display_name,
            has_required_coverage=has_required_coverage,
            score=float(c.discovery_score),
            score_threshold=PIPELINE_SCORE_THRESHOLD_V90,
            veto_reasons=veto_reasons,
            data_insufficient_reasons=data_insufficient_reasons,
        )
    return build_candidate_pipeline_trace_summary(tuple(by_key.values()))


def build_weekly_candidate_brief_v0(
    *,
    report_date: str | None = None,
    jp_universe_file: Path | None = None,
    us_universe_file: Path | None = None,
    scan_limit: int = 0,
    path_base: Path | None = None,
) -> WeeklyCandidateBriefV0:
    """Run JP+US discovery scans and assemble the weekly candidate brief."""

    root = path_base or ROOT_DIR
    run_date = report_date or date.today().isoformat()
    jp_themes = load_jp_theme_map(config_dir=root / "config" if (root / "config").is_dir() else CONFIG_DIR)
    us_themes = load_us_theme_map(config_dir=root / "config" if (root / "config").is_dir() else CONFIG_DIR)

    jp_result = scan_jp_universe(universe_file=jp_universe_file, limit=scan_limit)
    us_result = scan_us_universe(universe_file=us_universe_file, limit=scan_limit)

    jp_ranked, jp_insuf = _jp_rows(jp_result, jp_themes)
    us_ranked, us_insuf = _us_rows(us_result, us_themes)
    all_ranked = sorted(jp_ranked + us_ranked, key=_sort_key)
    all_insuf = jp_insuf + us_insuf

    top_picks, coverage_note = select_diversified_top_picks(
        jp_ranked=jp_ranked,
        us_ranked=us_ranked,
        all_ranked=all_ranked,
    )

    rapid_src = [c for c in all_ranked if "rapid_mover" in c.categories]
    pullback_src = [c for c in all_ranked if is_pullback_candidate(c)]
    avoid_src = [c for c in all_ranked if is_avoid_candidate(c)]
    insuf_src = sorted(all_insuf, key=_sort_key)[:SECTION_TOP_COUNT]

    rapid_movers = [_make_card(c, "rapid_mover") for c in rapid_src[:SECTION_TOP_COUNT]]
    pullbacks = [_make_card(c, "pullback") for c in pullback_src[:SECTION_TOP_COUNT]]
    avoid_list = [_make_card(c, "avoid") for c in avoid_src[:SECTION_TOP_COUNT]]
    insufficient_list = [_make_card(c, "insufficient") for c in insuf_src]
    theme_highlights = _dedupe_cards_by_symbol(_theme_highlights(all_ranked))
    pipeline_trace = _build_pipeline_trace_summary(
        ranked=all_ranked,
        insufficient=all_insuf,
        avoid_candidates=avoid_src,
    )

    appendix = (
        f"- JP スキャン: `{jp_result.universe_scope}` · {jp_result.symbol_count} 銘柄",
        f"- US スキャン: `{us_result.universe_scope}` · {us_result.symbol_count} 銘柄",
        "- インフラ診断（P3 / observation_log）は `weekly-observation-report-v1` を参照",
        f"- {DISCOVERY_SCORE_DISCLAIMER}",
    )

    discovery_merge = merge_cross_market_json_payloads(
        format_jp_discovery_json(jp_result),
        format_us_discovery_json(us_result),
    )

    return WeeklyCandidateBriefV0(
        report_date=run_date,
        generated_at_jp=jp_result.generated_at,
        generated_at_us=us_result.generated_at,
        jp_scope=jp_result.universe_scope,
        us_scope=us_result.universe_scope,
        macro_summary=_macro_summary(us_ranked),
        top_picks=top_picks,
        rapid_movers=rapid_movers,
        pullbacks=pullbacks,
        avoid_list=avoid_list,
        insufficient_list=insufficient_list,
        theme_highlights=theme_highlights,
        appendix_lines=appendix,
        coverage_note=coverage_note,
        discovery_merge=discovery_merge,
        pipeline_trace=pipeline_trace,
        score_veto_assessments=build_fixture_integrated_candidate_assessments_v93(),
    )


def _format_card_md(index: int, card: CandidateCard) -> list[str]:
    c = card.candidate
    type_ja = {
        "top_pick": "今週の注目",
        "rapid_mover": "急騰",
        "pullback": "押し目",
        "theme": "テーマ",
        "avoid": "避ける",
        "insufficient": "データ不足",
    }.get(card.brief_type, card.brief_type)
    market_ja = "日本" if c.market == MARKET_JP else "米国"
    lines = [
        f"### {index}. {c.display_name}（{market_ja} · score {c.discovery_score}）",
        "",
        f"- **種別**: {type_ja}",
        f"- **理由**: {card.reason}",
        "- **反証**:",
    ]
    for item in card.counter_evidence:
        lines.append(f"  - {item}")
    lines.append("- **次に確認**:")
    for item in card.next_checks:
        lines.append(f"  - {item}")
    if c.themes:
        lines.append(f"- **テーマ**: {', '.join(c.themes)}")
    lines.append("")
    return lines


COPY_READY_MARKER_FROM = "<<< COPY FROM HERE >>>"
COPY_READY_MARKER_TO = "<<< COPY TO HERE >>>"
COPY_READY_TABLE_MAX_CELL = 120


def _escape_md_table_cell(text: str, *, max_len: int = COPY_READY_TABLE_MAX_CELL) -> str:
    compact = " ".join(text.replace("|", "/").replace("\n", " ").split())
    if not compact:
        return "—"
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


def _truncate(text: str, *, max_len: int) -> str:
    compact = " ".join(text.replace("\n", " ").split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


def _strip_reason_prefix_for_copy(reason: str) -> str:
    # Copy-only should be compact and stable for one-click paste.
    prefixes = (
        "注目理由: ",
        "急騰の観測理由: ",
        "押し目の観測理由: ",
        "テーマの観測理由: ",
        "回避の観測理由: ",
        "要注意（データ不足）: ",
    )
    for p in prefixes:
        if reason.startswith(p):
            reason = reason[len(p) :]
            break
    # Drop trailing Japanese full stop for brevity.
    if reason.endswith("。"):
        reason = reason[:-1]
    return reason


def _copy_ready_type_for_top5(card: CandidateCard) -> str:
    c = card.candidate
    return "指数連動" if candidate_group(c) == "etf_proxy" else "注目"


def _format_copy_ready_brief_table_row(*, rank: int, card: CandidateCard) -> str:
    c = card.candidate
    t = _copy_ready_type_for_top5(card)
    short_reason = _strip_reason_prefix_for_copy(card.reason)
    short_reason = _truncate(short_reason, max_len=44)
    return (
        "| "
        + " | ".join(
            [
                str(rank),
                _escape_md_table_cell(c.instrument_id, max_len=24),
                _escape_md_table_cell(_copy_ready_name(c), max_len=32),
                _copy_ready_market(c),
                t,
                _escape_md_table_cell(short_reason, max_len=44),
            ]
        )
        + " |"
    )


def _format_copy_ready_candidate_memo(*, rank: int, card: CandidateCard) -> list[str]:
    c = card.candidate

    counter0 = card.counter_evidence[0] if card.counter_evidence else "（該当なし）"
    counter0 = counter0.replace("\n", " ")
    counter0 = _truncate(counter0, max_len=70)

    next0 = card.next_checks[0] if card.next_checks else "（該当なし）"
    next0 = next0.replace("\n", " ")
    next0 = _truncate(next0, max_len=78)

    title = f"### {rank}. {c.instrument_id} {_copy_ready_name(c)}"
    return [
        title,
        f"- 反証: {counter0}",
        f"- 次確認: {next0}",
        "",
    ]


def _copy_ready_market(c: UnifiedCandidate) -> str:
    if c.market == MARKET_JP:
        return "JP"
    if candidate_group(c) == "etf_proxy":
        return "ETF"
    return "US"


def _copy_ready_name(c: UnifiedCandidate) -> str:
    sym = c.instrument_id.strip()
    dn = c.display_name.strip()
    if dn.upper().startswith(sym.upper()):
        rest = dn[len(sym) :].strip()
        return rest or dn
    return dn


def _total_candidate_count(brief: WeeklyCandidateBriefV0) -> int:
    seen: set[str] = set()
    for cards in (
        brief.top_picks,
        brief.rapid_movers,
        brief.pullbacks,
        brief.avoid_list,
        brief.insufficient_list,
        brief.theme_highlights,
    ):
        for card in cards:
            c = card.candidate
            seen.add(f"{c.market}:{c.instrument_id}")
    return len(seen)


def _has_actionable_top_candidates(brief: WeeklyCandidateBriefV0) -> bool:
    return bool(brief.top_picks)


def _resolve_score_veto_assessments(
    brief: WeeklyCandidateBriefV0,
) -> tuple[CandidateIntegratedAssessment, ...] | None:
    if brief.score_veto_assessments:
        return brief.score_veto_assessments
    if _has_actionable_top_candidates(brief):
        return build_fixture_integrated_candidate_assessments_v93()
    return None


def _score_veto_pipeline_source(brief: WeeklyCandidateBriefV0) -> str:
    if brief.score_veto_assessments:
        return "explicit_assessments"
    if _has_actionable_top_candidates(brief):
        return "fixture_fallback_top_picks"
    return "empty_no_top_picks"


def _coverage_reason_codes_for_brief(brief: WeeklyCandidateBriefV0) -> tuple[str, ...]:
    if not brief.coverage_note:
        return ()
    raw = brief.coverage_note.removeprefix("coverage_note: ").strip()
    return tuple(code.value for code in parse_coverage_reason_codes_from_english(raw))


def _no_candidate_reason(brief: WeeklyCandidateBriefV0, *, user_facing: bool = True) -> str:
    if brief.top_picks:
        return "上位候補はあります。反証と次確認を優先して深掘りしてください。"
    if brief.coverage_note:
        note = brief.coverage_note.removeprefix("coverage_note: ").strip()
        if note:
            return translate_user_facing_coverage_reason_to_ja(note) if user_facing else note
    coverage_count = len(brief.insufficient_list)
    veto_count = len(brief.avoid_list)
    score_state = "該当候補なし" if coverage_count == 0 and veto_count == 0 else "coverage/veto確認を優先"
    return (
        f"候補0件の主因: coverage不足 {coverage_count}件 / "
        f"score未達 {score_state} / veto {veto_count}件。"
    )


def _weekly_conclusion_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    top_count = len(brief.top_picks)
    if top_count:
        total_count = _total_candidate_count(brief)
        return [
            "## 今週の結論",
            "",
            f"深掘り候補: {top_count}件。反証と次確認を先に見て、観測ベースで優先順位を確認します。",
            f"- 候補総数: {total_count}件 / 上位候補: {top_count}件",
            f"- 判断方針: {PORTFOLIO_ACTION_BIAS_V81}",
            "- 候補銘柄は「買い指示」ではなく、調査・監視・整理候補として扱う。",
            "- actual import / broker連携 / cache write は引き続き NO-GO。",
            "",
        ]
    reason_ja = _no_candidate_reason(brief)
    return [
        "## 今週の結論",
        "",
        "今週は新規買いを急がない。",
        "",
        "理由:",
        "- 現金比率が11.7%で、最低目安15%を下回っている",
        "- 個別株比率が19.6%で、目安10〜15%を上回っている",
        f"- {reason_ja}",
        "",
        "候補0件は「問題なし」ではなく、新規リスクを増やさない抑制シグナルです。",
        "",
        "今週やること:",
        "1. 新規リスク追加ではなく、現金回復と個別株比率の整理候補を確認",
        "2. データ不足の原因を確認",
        "3. 次回runで候補抽出が改善するかを見る",
        "",
        "今週やらないこと:",
        "- 根拠不足の個別株・高ベータ銘柄を追加しない",
        "- 候補0件を「問題なし」と解釈しない",
        "- actual import / broker連携 / cache write は引き続き NO-GO",
        "",
    ]


def _portfolio_constraint_lines() -> list[str]:
    return [
        "## ポートフォリオ制約",
        "",
        f"- 前提: {PORTFOLIO_CONTEXT_V81['source']}",
        f"- 総資産: {PORTFOLIO_CONTEXT_V81['total_assets']}",
        f"- 現金: {PORTFOLIO_CONTEXT_V81['cash']}（{PORTFOLIO_CONTEXT_V81['cash_policy']}）",
        f"- 株式系合計: {PORTFOLIO_CONTEXT_V81['equity_total']}",
        f"- 個別株: {PORTFOLIO_CONTEXT_V81['individual_stocks']}（{PORTFOLIO_CONTEXT_V81['individual_policy']}）",
        f"- 債券: {PORTFOLIO_CONTEXT_V81['bonds']} / GOLD: {PORTFOLIO_CONTEXT_V81['gold']}",
        f"- 高ベータ枠: {PORTFOLIO_CONTEXT_V81['crypto_high_beta']} / レバ枠: {PORTFOLIO_CONTEXT_V81['leverage']}",
        f"- 週次判断: {PORTFOLIO_ACTION_BIAS_V81}",
        "",
    ]


def _target_allocation_gap_short_lines() -> list[str]:
    # v82: 現在配分と目標配分の差分（観測・検証用）
    return format_target_allocation_gap_markdown_short_v82(_TARGET_ALLOCATION_GAP_V82)


def _action_classification_rows(brief: WeeklyCandidateBriefV0) -> list[tuple[str, int, str]]:
    top_count = len(brief.top_picks)
    watch_count = len(_dedupe_cards_by_symbol([*brief.rapid_movers, *brief.pullbacks, *brief.theme_highlights]))
    avoid_count = len(brief.avoid_list)
    data_blocked_count = len(brief.insufficient_list)
    return [
        (
            "新規リスク候補",
            top_count,
            "候補0件なら新規リスク追加を抑制" if top_count == 0 else "反証確認後に深掘り",
        ),
        ("監視候補", watch_count, "監視対象なし、またはデータ不足" if watch_count == 0 else "条件待ち"),
        ("追いかけない候補", avoid_count, "過熱判定対象なし" if avoid_count == 0 else "急伸後の反証を優先"),
        ("整理候補", 0, "実行判断ではなく、根拠確認と重複リスク確認を優先"),
        (
            "データ不足候補",
            data_blocked_count,
            "データ不足候補なし" if data_blocked_count == 0 else "coverage・価格・score内訳を確認",
        ),
        (
            "何もしない",
            1 if top_count == 0 else 0,
            "候補0件は失敗ではなく、抑制判断として記録" if top_count == 0 else "上位候補ありでも現金制約を優先",
        ),
    ]


def _action_classification_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    lines = [
        "## 行動分類",
        "",
        "| 分類 | 件数 | 判断 |",
        "|---|---:|---|",
    ]
    for label, count, judgement in _action_classification_rows(brief):
        lines.append(f"| {label} | {count} | {judgement} |")
    lines.append("")
    return lines


def _candidate_zero_reason_rows(brief: WeeklyCandidateBriefV0) -> list[tuple[str, str, str, str]]:
    coverage_count = len(brief.insufficient_list)
    veto_count = len(brief.avoid_list)
    score_state = "該当候補なし" if coverage_count == 0 and veto_count == 0 else "coverage/veto確認を優先"
    return [
        (
            "coverage不足",
            f"{coverage_count}件",
            "データ不足候補はcoverage不足として扱い、score判定の信頼度が不足",
            "価格・出来高・期間・データソースを確認",
        ),
        (
            "score未達",
            score_state,
            "score条件を満たす根拠が不足、または候補化前の条件確認が必要",
            "score内訳・閾値・相場環境を確認",
        ),
        (
            "veto",
            f"{veto_count}件",
            (
                "veto該当候補あり。除外理由の根拠を確認"
                if veto_count
                else "vetoで除外されたのではなく、主にcoverage/score条件で候補化されていない"
            ),
            "veto理由・除外条件・反証軸を確認",
        ),
    ]


def _candidate_zero_reason_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    if brief.top_picks:
        return []
    rows = _candidate_zero_reason_rows(brief)
    lines = [
        "## 候補0件の内訳",
        "",
        "| 理由カテゴリ | 件数/状態 | 説明 | 次に確認すること |",
        "|---|---|---|---|",
    ]
    for category, count_or_state, description, next_check in rows:
        lines.append(f"| {category} | {count_or_state} | {description} | {next_check} |")
    lines.append("")
    return lines


def _pipeline_trace_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    t = brief.pipeline_trace
    if t is None:
        avoid_ids = {f"{card.candidate.market}:{card.candidate.instrument_id}" for card in brief.avoid_list}
        t = build_candidate_pipeline_trace_summary(
            (
                CandidateTraceInput(
                    symbol=card.candidate.instrument_id,
                    name=card.candidate.display_name,
                    has_required_coverage=card.candidate.data_quality == "ok",
                    score=float(card.candidate.discovery_score),
                    score_threshold=PIPELINE_SCORE_THRESHOLD_V90,
                    veto_reasons=(
                        tuple(
                            sorted(
                                {
                                    x
                                    for x in {*card.candidate.categories, *card.candidate.labels}
                                    if ("caution" in x) or ("veto" in x)
                                }
                            )
                        )
                        or ("generic_veto",)
                    )
                    if f"{card.candidate.market}:{card.candidate.instrument_id}" in avoid_ids
                    else (),
                    data_insufficient_reasons=("insufficient_data",)
                    if card in brief.insufficient_list
                    else (),
                )
                for card in [*brief.top_picks, *brief.rapid_movers, *brief.pullbacks, *brief.avoid_list, *brief.insufficient_list]
            )
        )
    lines = [
        "## 候補パイプライン・トレース",
        "",
        "この表は売買指示ではなく、候補がどの段階で止まったかを確認するためのものです。",
        "",
        "| 段階 | 件数 | 説明 | 次に確認すること |",
        "|---|---:|---|---|",
        f"| 入力候補 | {t.input_count} | 週次評価に入った候補数 | universe / source |",
        (
            f"| coverage不足 | {t.coverage_missing_count} | "
            "必要データ不足でscore信頼度が不足 | 価格・出来高・期間・データソース |"
        ),
        f"| score未達 | {t.score_miss_count} | score条件を満たさなかった候補 | score内訳・閾値 |",
        f"| veto該当 | {t.veto_count} | 安全側の除外条件に該当した候補 | veto詳細 |",
        (
            f"| 深掘り可能候補 | {t.final_candidate_count} | "
            "score条件を満たしvetoなしの候補（買い推奨ではない） | 個別確認・反証 |"
        ),
        "",
        (
            f"- 候補パイプライン: 入力{t.input_count} / coverage不足{t.coverage_missing_count} / "
            f"score未達{t.score_miss_count} / veto{t.veto_count} / 深掘り可能{t.final_candidate_count}"
        ),
    ]
    if t.final_candidate_count == 0:
        lines.append(
            "- 今回は深掘り可能候補0件です。これは買い推奨候補がない意味ではなく、"
            "coverage/score/veto条件上、強い新規リスク候補として扱える根拠が不足している状態です。"
        )
    if t.coverage_missing_count >= t.score_miss_count and t.coverage_missing_count >= t.veto_count:
        lines.append("- 主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。")
    lines.extend(["", "### Veto reason log", ""])
    if not t.veto_reason_log:
        lines.extend(
            [
                "veto reason log: 該当なし。今回はvetoで除外されたというより、coverageまたはscore条件で候補化されていません。",
                "",
            ]
        )
        return lines
    lines.extend(
        [
            "| 候補 | veto | 説明 | 次確認 |",
            "|---|---|---|---|",
        ]
    )
    for row in t.veto_reason_log:
        lines.append(f"| {row.symbol} | {row.veto_key} | {row.description_ja} | {row.next_check_ja} |")
    lines.append("")
    return lines


def _score_veto_integration_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    assessments = _resolve_score_veto_assessments(brief)
    if not assessments:
        return [
            "## Score / Veto 統合サマリー",
            "",
            "今回は強い新規候補0件のため、パイプライン候補表は表示しません。",
            "coverage / score / veto 条件の確認を優先してください。",
            "",
        ]
    return render_integrated_candidate_assessment_markdown(assessments).splitlines() + [""]


def _monthly_input_summary_lines_v95() -> tuple[str, ...]:
    fixture = build_redacted_monthly_portfolio_fixture_v95()
    result = validate_monthly_portfolio_input_v95(fixture, current_month=fixture.as_of_month)
    core = render_monthly_input_consistency_summary_lines_v95(fixture, result)
    return (
        f"Monthly Input: 判定 {result.overall_severity.value.upper()} / 対象月 {fixture.as_of_month}",
        f"Monthly Guardrail: 現金{fixture.cash.ratio_pct:.1f}% / 個別株{fixture.individual_stocks.ratio_pct:.1f}%",
        core[2],
        core[3],
    )


def _shared_view_model_lines_v96(brief: WeeklyCandidateBriefV0) -> list[str]:
    assessments = _resolve_score_veto_assessments(brief)
    if assessments:
        score_veto_summary = render_integrated_candidate_assessment_summary_lines(assessments)
    else:
        score_veto_summary = (
            "Score/Veto: 深掘り候補0。強い新規候補なしのためfixture候補表は表示しません。",
            "これは実行指示ではなく、根拠補完と安全確認の分類です。",
        )
    t = brief.pipeline_trace
    if t is None:
        pipeline_summary = ("候補パイプライン: 集計情報なし",)
    else:
        pipeline_summary = (
            f"候補パイプライン: 入力{t.input_count} / coverage不足{t.coverage_missing_count} / score未達{t.score_miss_count} / veto{t.veto_count} / 深掘り可能{t.final_candidate_count}",
            "主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。",
        )
    model = build_weekly_shared_view_model_v96(
        score_veto_summary_lines=score_veto_summary,
        pipeline_summary_lines=pipeline_summary,
        monthly_input_summary_lines=_monthly_input_summary_lines_v95(),
        sanitized_manual_input_summary_lines=build_sanitized_manual_input_summary_lines_v99(),
    )
    return render_weekly_shared_view_model_markdown_v96(model)


def _do_dont_lines() -> list[str]:
    lines = ["## 今週のDo / Don't", "", "### Do"]
    lines.extend(f"- {item}" for item in DO_ITEMS_V81)
    lines.extend(["", "### Don't"])
    lines.extend(f"- {item}" for item in DONT_ITEMS_V81)
    lines.append("")
    return lines


def _cleanup_priority_rows(brief: WeeklyCandidateBriefV0) -> tuple[CleanupPriorityRow, ...]:
    data_blocked_count = len(brief.insufficient_list)
    top_count = len(brief.top_picks)
    evidence_gap_score = 3 if data_blocked_count or top_count == 0 else 2
    evidence_gap_reason = (
        f"データ不足候補 {data_blocked_count}件。coverage / score / veto理由を確認"
        if data_blocked_count
        else "候補根拠はあるが、反証・データ鮮度・veto理由の確認が先"
    )
    if top_count == 0 and data_blocked_count == 0:
        evidence_gap_reason = "候補0件。coverage / score / veto理由を確認"
    return (
        CleanupPriorityRow(
            target="個別株枠",
            classification="個別株全体",
            priority=4,
            cash_pressure=4,
            allocation_excess=4,
            evidence_gap=2,
            volatility_risk=2,
            duplication_risk=3,
            main_reason="個別株19.6%で10〜15%方向の目安を上回り、現金11.7%も不足",
            weekly_treatment="新規追加を抑制し、重複リスクと整理候補の根拠を確認",
        ),
        CleanupPriorityRow(
            target="高ボラ枠",
            classification="仮想通貨・高ベータ",
            priority=3,
            cash_pressure=4,
            allocation_excess=1,
            evidence_gap=2,
            volatility_risk=4,
            duplication_risk=2,
            main_reason="高ベータ枠1.3%は小さいが、現金不足下では追加リスクを抑制",
            weekly_treatment="追加せず監視し、既存リスクとの相関を確認",
        ),
        CleanupPriorityRow(
            target="株式系重複リスク",
            classification="INDEX + 個別株",
            priority=4,
            cash_pressure=4,
            allocation_excess=3,
            evidence_gap=2,
            volatility_risk=2,
            duplication_risk=4,
            main_reason="株式系67.8%で、INDEXと個別株の同方向リスクが積み上がりやすい",
            weekly_treatment="新規テーマ追加より、重複テーマ・セクター偏りを確認",
        ),
        CleanupPriorityRow(
            target="データ不足候補",
            classification="candidate group",
            priority=evidence_gap_score,
            cash_pressure=3,
            allocation_excess=2,
            evidence_gap=evidence_gap_score,
            volatility_risk=2,
            duplication_risk=2,
            main_reason=evidence_gap_reason,
            weekly_treatment="深掘り前にcoverage・価格・score内訳を補完",
        ),
    )


def _cleanup_priority_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    lines = [
        "## 整理・監視優先度スコア",
        "",
        CLEANUP_PRIORITY_NOTE_V83,
        "",
        "| 対象 | 分類 | 優先度 | 主な理由 | 今週の扱い |",
        "|---|---|---:|---|---|",
    ]
    for row in _cleanup_priority_rows(brief):
        lines.append(
            f"| {row.target} | {row.classification} | {row.priority} | "
            f"{row.main_reason} | {row.weekly_treatment} |"
        )
    lines.extend(
        [
            "",
            "### スコアリング軸",
            "",
            "| 対象 | 現金圧力 | 配分超過 | 根拠不足 | 高ボラリスク | 重複リスク |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in _cleanup_priority_rows(brief):
        lines.append(
            f"| {row.target} | {row.cash_pressure} | {row.allocation_excess} | "
            f"{row.evidence_gap} | {row.volatility_risk} | {row.duplication_risk} |"
        )
    lines.extend(["", "### スコアの見方"])
    lines.extend(f"- {item}" for item in CLEANUP_SCORE_SCALE_V83)
    lines.append("")
    return lines


def _weekly_action_checklist_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    if not _has_actionable_top_candidates(brief):
        lines = ["## 次に確認すること", ""]
        lines.extend(f"- {item}" for item in NEXT_CHECK_ITEMS_V85)
        lines.append("- score 4以上の枠が、個別株・高ボラ枠・重複リスクのどれに集中しているか")
        lines.append("")
        return lines
    lines = ["## 今週の行動チェックリスト", "", "### 今週やってよいこと"]
    lines.extend(f"- {item}" for item in ALLOWED_ACTION_ITEMS_V85)
    lines.append("- 整理・監視優先度スコアが高い枠の根拠を確認する")
    lines.extend(["", "### 今週やらないこと"])
    lines.extend(f"- {item}" for item in SUPPRESSED_ACTION_ITEMS_V85)
    lines.append("- 整理・監視優先度が高い枠と同じリスクを新規に増やさない")
    lines.extend(["", "### 次に確認すること"])
    lines.extend(f"- {item}" for item in NEXT_CHECK_ITEMS_V85)
    lines.append("- score 4以上の枠が、個別株・高ボラ枠・重複リスクのどれに集中しているか")
    lines.append("")
    return lines


def _chatgpt_review_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    return [
        "## ChatGPTレビュー依頼",
        "",
        "この週次レポートを、追加煽りを避けて、cleanup / risk-control / data-quality優先でレビューしてください。",
        f"- report_date: {brief.report_date}",
        "- run_type: local_or_workflow_generated",
        f"- candidate_count: {_total_candidate_count(brief)}",
        f"- no_candidate_reason: {_no_candidate_reason(brief)}",
        f"- portfolio_context: cash {PORTFOLIO_CONTEXT_V81['cash']}, individual stocks {PORTFOLIO_CONTEXT_V81['individual_stocks']}, equity total {PORTFOLIO_CONTEXT_V81['equity_total']}",
        "- cleanup_priority: 現金圧力 / 配分超過 / 根拠不足 / 高ボラリスク / 重複リスク を確認してください。",
        "- review_request: 今週やってよいこと / やらないこと / 次に確認することを、現金制約と個別株比率制約から再点検してください。",
        "",
    ]


def _safety_action_note_lines() -> list[str]:
    return [
        "## 安全メモ",
        "",
        "これは売買指示ではありません。",
        "現金比率が低い局面では、候補が出ないこと自体を「新規リスクを増やさない」抑制シグナルとして扱います。",
        "actual import / broker連携 / cache write / 実メール送信は実行していません。",
        "",
    ]


def _format_copy_ready_block_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    lines = [
        COPY_READY_MARKER_FROM,
        f"# 週次候補ブリーフ — {brief.report_date}",
        "",
    ]
    lines.extend(_weekly_conclusion_lines(brief))
    lines.extend(_portfolio_constraint_lines())
    lines.extend(_target_allocation_gap_short_lines())
    lines.extend(_action_classification_lines(brief))
    lines.extend(_pipeline_trace_lines(brief))
    lines.extend(_score_veto_integration_lines(brief))
    lines.extend(_shared_view_model_lines_v96(brief))
    lines.extend(_candidate_zero_reason_lines(brief))
    lines.extend(_cleanup_priority_lines(brief))
    lines.extend(_weekly_action_checklist_lines(brief))
    if _has_actionable_top_candidates(brief):
        lines.extend(_do_dont_lines())
    lines.extend(
        [
            "## 今週の深掘り候補 上位5件",
            "",
            "| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for rank, card in enumerate(brief.top_picks, start=1):
        lines.append(_format_copy_ready_brief_table_row(rank=rank, card=card))
    if not brief.top_picks:
        lines.append("| — | — | — | — | — | — |")
    if brief.coverage_note and _has_actionable_top_candidates(brief):
        lines.extend(["", f"- coverage: {_no_candidate_reason(brief)}"])

    lines.extend(
        [
            "",
            "## 候補別メモ",
            "",
        ]
    )
    if brief.top_picks:
        for rank, card in enumerate(brief.top_picks, start=1):
            lines.extend(_format_copy_ready_candidate_memo(rank=rank, card=card))
    else:
        lines.extend(
            [
                "- （該当なし）",
                "",
            ]
        )
    lines.extend(
        [
            "",
            "## 見方",
            "- これは観測・深掘り候補の整理であり、売買推奨ではありません。",
            "- 上位5件は JP / US / ETF の横断性を優先します。",
            "- 反証と次確認を見て、深掘りする候補を選びます。",
            "",
        ]
    )
    lines.extend(_chatgpt_review_lines(brief))
    lines.extend(_safety_action_note_lines())
    lines.append(COPY_READY_MARKER_TO)
    return lines


def format_weekly_candidate_brief_v0_copy(brief: WeeklyCandidateBriefV0) -> str:
    """Copy-only body: markers, Top5 table, and 見方 (no full report sections)."""

    body = "\n".join(_format_copy_ready_block_lines(brief))
    if not body.endswith("\n"):
        body += "\n"
    assert_no_forbidden_terms(body)
    return body


def _format_copy_ready_summary(brief: WeeklyCandidateBriefV0) -> list[str]:
    return [
        "## コピー用サマリー",
        "",
        *_format_copy_ready_block_lines(brief),
        "",
    ]


def _format_cards_section(title: str, cards: Sequence[CandidateCard]) -> list[str]:
    lines = [f"## {title}", ""]
    if not cards:
        lines.append("- （該当なし）")
        lines.append("")
        return lines
    for i, card in enumerate(cards, start=1):
        lines.extend(_format_card_md(i, card))
    return lines


def format_weekly_candidate_brief_v0_markdown(brief: WeeklyCandidateBriefV0) -> str:
    lines = [
        "# 週次候補ブリーフ v0.1",
        "",
        BRIEF_DISCLAIMER_JA,
        "",
        OBSERVATION_DISCLAIMER,
        "",
        f"レポート日: **{brief.report_date}**",
        f"- JP 生成: {brief.generated_at_jp} · scope `{brief.jp_scope}`",
        f"- US 生成: {brief.generated_at_us} · scope `{brief.us_scope}`",
        "",
    ]
    lines.extend(_format_copy_ready_summary(brief))
    lines.extend(
        [
            "## マクロ環境（ETF proxy）",
            "",
            brief.macro_summary,
            "",
        ]
    )
    lines.extend(_format_cards_section("今週の候補 Top 5（横断）", brief.top_picks))
    if brief.coverage_note:
        raw_note = brief.coverage_note.removeprefix("coverage_note: ").strip()
        lines.append(f"- coverage補足: {translate_user_facing_coverage_reason_to_ja(raw_note)}")
        lines.append("")
    lines.extend(_format_cards_section("急騰候補 Top 3", brief.rapid_movers))
    lines.extend(_format_cards_section("押し目候補 Top 3", brief.pullbacks))
    lines.extend(_format_cards_section("過熱・避ける候補 Top 3", brief.avoid_list))
    lines.extend(_format_cards_section("データ不足・要注意 Top 3", brief.insufficient_list))
    lines.extend(_format_cards_section("テーマハイライト", brief.theme_highlights))
    lines.extend(["## 付録（運用）", ""])
    lines.extend(list(brief.appendix_lines))
    lines.append("")
    lines.extend(
        [
            "## 再生成コマンド",
            "",
            "- `.venv/bin/python -m invis_alpha_os.cli.main weekly-candidate-brief --format markdown`",
            "",
        ]
    )
    body = "\n".join(lines)
    assert_no_forbidden_terms(body)
    return body


def _card_to_dict(card: CandidateCard) -> dict[str, Any]:
    return {
        "brief_type": card.brief_type,
        "reason": card.reason,
        "counter_evidence": list(card.counter_evidence),
        "next_checks": list(card.next_checks),
        "candidate": asdict(card.candidate),
    }


def _integrated_assessment_to_dict(row: CandidateIntegratedAssessment) -> dict[str, Any]:
    return asdict(row)


def format_weekly_candidate_brief_v0_json(brief: WeeklyCandidateBriefV0) -> str:
    payload: dict[str, Any] = {
        "schema_version": "weekly_candidate_brief.v0.1",
        "report_date": brief.report_date,
        "macro_summary": brief.macro_summary,
        "jp_scope": brief.jp_scope,
        "us_scope": brief.us_scope,
        "sections": {
            "top_picks": [_card_to_dict(c) for c in brief.top_picks],
            "rapid_movers": [_card_to_dict(c) for c in brief.rapid_movers],
            "pullbacks": [_card_to_dict(c) for c in brief.pullbacks],
            "avoid": [_card_to_dict(c) for c in brief.avoid_list],
            "insufficient": [_card_to_dict(c) for c in brief.insufficient_list],
            "theme_highlights": [_card_to_dict(c) for c in brief.theme_highlights],
        },
        "score_veto_pipeline": [
            _integrated_assessment_to_dict(row)
            for row in (_resolve_score_veto_assessments(brief) or ())
        ],
        "score_veto_pipeline_source": _score_veto_pipeline_source(brief),
        "coverage_reason_codes": list(_coverage_reason_codes_for_brief(brief)),
        "discovery": brief.discovery_merge,
        "observation_only": True,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    assert_no_forbidden_terms(text)
    return text
