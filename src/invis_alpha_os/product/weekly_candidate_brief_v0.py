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


def _format_copy_ready_block_lines(brief: WeeklyCandidateBriefV0) -> list[str]:
    lines = [
        COPY_READY_MARKER_FROM,
        f"# 週次候補ブリーフ — {brief.report_date}",
        "",
        "## 今週の深掘り候補 上位5件",
        "",
        "| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |",
        "|---|---|---|---|---|---|",
    ]
    for rank, card in enumerate(brief.top_picks, start=1):
        lines.append(_format_copy_ready_brief_table_row(rank=rank, card=card))
    if not brief.top_picks:
        lines.append("| — | — | — | — | — | — |")

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
            COPY_READY_MARKER_TO,
        ]
    )
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
        lines.append("- " + brief.coverage_note)
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
        "discovery": brief.discovery_merge,
        "observation_only": True,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    assert_no_forbidden_terms(text)
    return text
