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

MACRO_PROXY_SYMBOLS: tuple[str, ...] = ("SPY", "TLT", "GLDM", "SLV")

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


def build_counter_evidence(c: UnifiedCandidate) -> tuple[str, ...]:
    out: list[str] = []
    if "overheated_caution" in c.categories or "overheat_caution" in c.labels:
        out.append(
            f"過熱ラベル: 20日 {format_pct(c.return_20d)} / 60日 {format_pct(c.return_60d)} — "
            "短期の急伸後は調整リスクが高い。"
        )
    if "low_liquidity_caution" in c.labels:
        out.append("流動性注意: 出来高・スプレッドを確認し、観測スコアだけで深掘りしない。")
    if c.return_5d is not None and c.return_5d < PULLBACK_R5_MIN:
        out.append(f"直近5日が {format_pct(c.return_5d)} と弱く、トレンド崩れの可能性がある。")
    if "insufficient_data" in c.categories:
        out.append("データ不足: キャッシュ履歴が短いか欠損。ラベル・リターンを信用しない。")
    if not out:
        out.append("モメンタムは一方向。マクロ・決算・セクター相対で無効化条件を確認する。")
    return tuple(out[:2])


def build_next_checks(c: UnifiedCandidate) -> tuple[str, ...]:
    checks: list[str] = []
    if c.market == MARKET_JP:
        checks.extend(
            [
                "直近の開示・ニュースとセクター背景",
                "決算・バリュエーション（テーマ持続性）",
                "既存保有・ウォッチリストとの重複",
            ]
        )
    else:
        checks.extend(
            [
                "直近の決算・ガイダンスとセクター相対",
                "流動性・スプレッド（特に ETF / プロキシ）",
                "指数・金利プロキシ（SPY/TLT）との整合",
            ]
        )
    if "volume_spike" in c.labels:
        checks.append("出来高スパイクの持続性（イベント駆動かどうか）")
    elif is_pullback_candidate(c):
        checks.append("押し目: 60日トレンド維持のまま5日調整か、反転シグナルか")
    return tuple(checks[:3])


def _make_card(c: UnifiedCandidate, brief_type: CandidateBriefType) -> CandidateCard:
    return CandidateCard(
        brief_type=brief_type,
        candidate=c,
        reason=c.reason,
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

    top_picks = [_make_card(c, "top_pick") for c in all_ranked[:TOP_PICK_COUNT]]

    rapid_src = [c for c in all_ranked if "rapid_mover" in c.categories]
    pullback_src = [c for c in all_ranked if is_pullback_candidate(c)]
    avoid_src = [c for c in all_ranked if is_avoid_candidate(c)]
    insuf_src = sorted(all_insuf, key=_sort_key)[:SECTION_TOP_COUNT]

    rapid_movers = [_make_card(c, "rapid_mover") for c in rapid_src[:SECTION_TOP_COUNT]]
    pullbacks = [_make_card(c, "pullback") for c in pullback_src[:SECTION_TOP_COUNT]]
    avoid_list = [_make_card(c, "avoid") for c in avoid_src[:SECTION_TOP_COUNT]]
    insufficient_list = [_make_card(c, "insufficient") for c in insuf_src]
    theme_highlights = _theme_highlights(all_ranked)

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
        "## マクロ環境（ETF proxy）",
        "",
        brief.macro_summary,
        "",
    ]
    lines.extend(_format_cards_section("今週の候補 Top 5（横断）", brief.top_picks))
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
