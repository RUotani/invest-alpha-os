"""Weekly Candidate Brief v0.1 — cross-market discovery primary output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.discovery.cross_market_contract import FORBIDDEN_OUTPUT_TERMS
from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    CandidateCard,
    UnifiedCandidate,
    build_counter_evidence,
    build_reason_human,
    candidate_group,
    build_weekly_candidate_brief_v0,
    format_weekly_candidate_brief_v0_copy,
    format_weekly_candidate_brief_v0_json,
    format_weekly_candidate_brief_v0_markdown,
    is_pullback_candidate,
    select_diversified_top_picks,
)

runner = CliRunner()


def _candidate(**overrides: object) -> UnifiedCandidate:
    base = dict(
        market="us",
        instrument_id="MSFT",
        display_name="MSFT",
        discovery_score=3,
        latest_date="2026-05-01",
        close=100.0,
        return_5d=-0.04,
        return_20d=0.08,
        return_60d=0.12,
        labels=("near_high",),
        categories=("near_high_quality_trend",),
        data_quality="ok",
        reason="surfaced: near_high",
        themes=("us_equity",),
        volume_status="normal",
    )
    base.update(overrides)
    return UnifiedCandidate(**base)  # type: ignore[arg-type]


def test_is_pullback_candidate_true() -> None:
    c = _candidate(return_5d=-0.04, return_20d=0.06, return_60d=0.10, categories=("near_high_quality_trend",))
    assert is_pullback_candidate(c) is True


def test_is_pullback_candidate_false_when_overheated() -> None:
    c = _candidate(categories=("overheated_caution",), labels=("overheat_caution",))
    assert is_pullback_candidate(c) is False


def test_build_counter_evidence_overheat() -> None:
    c = _candidate(categories=("overheated_caution", "rapid_mover"), labels=("overheat_caution",))
    ev = build_counter_evidence(c)
    assert any("過熱" in line for line in ev)


def test_format_markdown_has_candidate_sections() -> None:
    card = CandidateCard(
        brief_type="top_pick",
        candidate=_candidate(),
        reason="surfaced: near_high",
        counter_evidence=("反証1",),
        next_checks=("確認1", "確認2", "確認3"),
    )
    from invis_alpha_os.product.weekly_candidate_brief_v0 import WeeklyCandidateBriefV0

    brief = WeeklyCandidateBriefV0(
        report_date="2026-05-27",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="テスト macro",
        top_picks=[card],
    )
    md = format_weekly_candidate_brief_v0_markdown(brief)
    assert "# 週次候補ブリーフ v0.1" in md
    assert "## コピー用サマリー" in md
    assert "<<< COPY FROM HERE >>>" in md
    assert "## 今週の深掘り候補 上位5件" in md
    assert "| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |" in md
    assert "| 1 | MSFT |" in md
    assert "## 今週の候補 Top 5" in md
    assert "**反証**" in md
    assert "**次に確認**" in md
    lower = md.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert term not in lower


def test_format_json_schema() -> None:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import WeeklyCandidateBriefV0

    brief = WeeklyCandidateBriefV0(
        report_date="2026-05-27",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
        discovery_merge={"schema_version": "discovery.cross_market.v1"},
    )
    payload = json.loads(format_weekly_candidate_brief_v0_json(brief))
    assert payload["schema_version"] == "weekly_candidate_brief.v0.1"
    assert payload["sections"]["top_picks"] == []
    assert payload["score_veto_pipeline"][0]["symbol"] == "GRID_A"
    assert payload["score_veto_pipeline"][0]["pipeline_stage"] == "veto_blocked"


def test_v81_no_candidate_ux_blocks_are_rendered() -> None:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import WeeklyCandidateBriefV0

    brief = WeeklyCandidateBriefV0(
        report_date="2026-06-02",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
        coverage_note=(
            "coverage_note: JP candidates were unavailable due to insufficient JP cache quality / "
            "US equity candidates were unavailable due to insufficient data quality"
        ),
    )
    md = format_weekly_candidate_brief_v0_markdown(brief)
    copy_body = format_weekly_candidate_brief_v0_copy(brief)

    for body in (md, copy_body):
        assert "## 今週の結論" in body
        assert "強い新規リスク候補: 0件" in body
        assert "## ポートフォリオ制約" in body
        assert "現金: 508.2万円 / 11.7%" in body
        assert "個別株: 846.3万円 / 19.6%" in body
        assert "株式系合計: 2,934.5万円 / 67.8%" in body
        assert "## 目標配分ギャップ（v82）" in body
        assert "不足 790.2万円" in body
        assert "上回り +813.8万円" in body
        assert "## 行動分類" in body
        assert "| 新規リスク候補 | 0 | 候補0件なら新規リスク追加を抑制 |" in body
        assert "| データ不足候補 | 0 | データ不足候補なし |" in body
        assert "| 何もしない | 1 | 候補0件は失敗ではなく、抑制判断として記録 |" in body
        assert "## 候補パイプライン・トレース" in body
        assert "| 入力候補 |" in body
        assert "| coverage不足 |" in body
        assert "| score未達 |" in body
        assert "| veto該当 |" in body
        assert "| 深掘り可能候補 |" in body
        assert "深掘り可能候補0件です。これは買い推奨候補がない意味ではなく" in body
        assert "### Veto reason log" in body
        assert "veto reason log: 該当なし。" in body
        assert "候補パイプライン: 入力" in body
        assert "主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。" in body
        assert "## Score / Veto 統合サマリー" in body
        assert "| 候補 | Score band | Score | Veto | Pipeline | 今週の扱い | 次確認 |" in body
        assert "| CASH_D | HIGH_CONVICTION_REVIEW | 87.25 | - | high_conviction_review | 高優先レビュー |" in body
        assert "Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in body
        assert "これは実行指示ではなく、根拠補完と安全確認の分類です。" in body
        assert "## Shared Summary（v96）" in body
        assert "### Monthly Input Consistency（共有要約）" in body
        assert "Monthly Input: 判定 WARN / 対象月 2026-05" in body
        assert "Monthly Guardrail: 現金11.7% / 個別株19.6%" in body
        assert "### Sanitized / Manual Input（共有要約）" in body
        assert "Sanitized Input: 判定 WARN / 2026-05 / JPY / man_yen" in body
        assert "Sanitized Guardrail: 現金11.7%はminimum 15.0%未満" in body
        assert "Sanitized Parity: v97/v95整合 WARN" in body
        assert "## 候補0件の理由メモ" in body
        assert "| coverage不足 | 0件 |" in body
        assert "| score未達 | 該当候補なし |" in body
        assert "| veto | 0件 | vetoで除外されたのではなく" in body
        assert "候補0件の主因: coverage不足 0件 / score未達 該当候補なし / veto 0件" in body
        assert "次確認: 価格・出来高・期間・score内訳・veto理由" in body
        assert "vetoで除外されたのではなく、主にcoverage/score条件で候補化されていない" in body
        assert "## 整理・監視優先度スコア" in body
        assert "このスコアは売却指示ではなく、次に確認すべき整理・監視優先度です" in body
        assert "| 個別株枠 | 個別株全体 | 4 |" in body
        assert "| 株式系重複リスク | INDEX + 個別株 | 4 |" in body
        assert "| 高ボラ枠 | 仮想通貨・高ベータ | 3 |" in body
        assert "| データ不足候補 | candidate group | 3 |" in body
        assert "現金圧力" in body
        assert "配分超過" in body
        assert "根拠不足" in body
        assert "高ボラリスク" in body
        assert "重複リスク" in body
        assert "5: 強い抑制・新規追加禁止寄り" in body
        assert "## 今週の行動チェックリスト" in body
        assert "### 今週やってよいこと" in body
        assert "### 今週やらないこと" in body
        assert "### 次に確認すること" in body
        assert "候補0件の理由、coverage不足、score未達、veto理由を確認する" in body
        assert "現金11.7%から最低15%、できれば20%方向へ戻す前提" in body
        assert "個別株19.6%が10〜15%目安を上回る前提" in body
        assert "株式系67.8%と個別株19.6%に重複リスク" in body
        assert "整理・監視優先度スコアが高い枠の根拠を確認する" in body
        assert "整理・監視優先度が高い枠と同じリスクを新規に増やさない" in body
        assert "score 4以上の枠" in body
        assert "候補0件はレポート失敗ではありません" in body
        assert "## 今週のDo / Don't" in body
        assert "候補0件の理由とcoverage不足を確認する" in body
        assert "データ不足のまま個別株リスクを増やさない" in body
        assert "## ChatGPTレビュー依頼" in body
        assert "cleanup_priority" in body
        assert "今週やってよいこと / やらないこと / 次に確認すること" in body
        assert "no_candidate_reason" in body
        assert "## 安全メモ" in body
        assert "このレポートは売買指示ではありません" in body

    assert copy_body.strip().startswith("<<< COPY FROM HERE >>>")
    assert copy_body.strip().endswith("<<< COPY TO HERE >>>")
    lower = copy_body.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert term not in lower


def _candidate_jp(
    *,
    code: str = "7011",
    themes: tuple[str, ...] = ("energy",),
    labels: tuple[str, ...] = ("rapid_mover_20d", "near_high"),
    categories: tuple[str, ...] = ("rapid_mover", "near_high_quality_trend"),
    discovery_score: int = 10,
) -> UnifiedCandidate:
    return UnifiedCandidate(
        market="jp",
        instrument_id=code,
        display_name=code,
        discovery_score=discovery_score,
        latest_date="2026-05-01",
        close=100.0,
        return_5d=0.01,
        return_20d=0.12,
        return_60d=0.15,
        labels=labels,
        categories=categories,
        data_quality="ok",
        reason="surfaced: near_high, rapid_mover_20d",
        themes=themes,
        volume_status="normal",
    )


def _candidate_us_equity(
    *,
    symbol: str = "MSFT",
    themes: tuple[str, ...] = ("us_equity",),
    labels: tuple[str, ...] = ("rapid_mover_20d", "near_high"),
    categories: tuple[str, ...] = ("rapid_mover", "near_high_quality_trend"),
    discovery_score: int = 7,
    volume_spike: bool = False,
) -> UnifiedCandidate:
    final_labels = labels + (("volume_spike",) if volume_spike else ())
    return UnifiedCandidate(
        market="us",
        instrument_id=symbol,
        display_name=symbol,
        discovery_score=discovery_score,
        latest_date="2026-05-01",
        close=100.0,
        return_5d=-0.01,
        return_20d=0.08,
        return_60d=0.14,
        labels=final_labels,
        categories=categories,
        data_quality="ok",
        reason="surfaced: near_high, rapid_mover_20d",
        themes=themes,
        volume_status="normal",
    )


def _candidate_etf_proxy(
    *,
    symbol: str = "SPY",
    themes: tuple[str, ...] = ("us_etf",),
    labels: tuple[str, ...] = ("rapid_mover_20d",),
    categories: tuple[str, ...] = ("rapid_mover",),
    discovery_score: int = 6,
) -> UnifiedCandidate:
    return UnifiedCandidate(
        market="us",
        instrument_id=symbol,
        display_name=symbol,
        discovery_score=discovery_score,
        latest_date="2026-05-01",
        close=100.0,
        return_5d=0.0,
        return_20d=0.05,
        return_60d=0.09,
        labels=labels,
        categories=categories,
        data_quality="ok",
        reason="surfaced: rapid_mover_20d",
        themes=themes,
        volume_status="normal",
    )


def test_select_diversified_top_picks_mixes_jp_us_etf_proxy() -> None:
    jp = _candidate_jp(discovery_score=10, themes=("energy",))
    us_eq = _candidate_us_equity(symbol="MSFT", discovery_score=7, themes=("us_equity",))
    etf = _candidate_etf_proxy(symbol="SPY", discovery_score=6, themes=("us_etf",))

    # Fill remaining slots with arbitrary candidates; all_ranked order matters.
    extra_jp = _candidate_jp(code="7012", themes=("ai_infra",), discovery_score=9)
    extra_us = _candidate_us_equity(symbol="NVDA", discovery_score=8, themes=("us_equity",))

    all_ranked = [jp, extra_jp, us_eq, extra_us, etf]
    top, coverage_note = select_diversified_top_picks(
        jp_ranked=[jp, extra_jp],
        us_ranked=[us_eq, extra_us, etf],
        all_ranked=all_ranked,
    )

    assert coverage_note is None
    assert len(top) == 5
    groups = {candidate_group(card.candidate) for card in top}
    assert "jp" in groups
    assert "us_equity" in groups
    assert "etf_proxy" in groups


def test_reason_is_human_friendly_no_internal_tokens() -> None:
    jp = _candidate_jp(labels=("near_high", "rapid_mover_20d"))
    us_eq = _candidate_us_equity(labels=("near_high", "rapid_mover_20d"))
    etf = _candidate_etf_proxy(labels=("rapid_mover_20d",))

    r1 = build_reason_human(jp, "top_pick")
    r2 = build_reason_human(us_eq, "top_pick")
    r3 = build_reason_human(etf, "top_pick")

    for r in (r1, r2, r3):
        lower = r.lower()
        assert "surfaced" not in lower
        assert "rapid_mover" not in lower
        assert "near_high" not in lower
        assert "overheat_caution" not in lower


def test_next_checks_diversity_among_top_picks() -> None:
    jp = _candidate_jp(discovery_score=10, themes=("energy",))
    us_eq = _candidate_us_equity(symbol="MSFT", discovery_score=7, themes=("us_equity",))
    etf = _candidate_etf_proxy(symbol="TLT", discovery_score=6, themes=("us_etf",))
    extra_jp = _candidate_jp(code="7012", themes=("ai_infra",), discovery_score=9)
    extra_us = _candidate_us_equity(symbol="NVDA", discovery_score=8, themes=("us_equity",), volume_spike=True)

    all_ranked = [jp, extra_jp, us_eq, extra_us, etf]
    top, _cn = select_diversified_top_picks(
        jp_ranked=[jp, extra_jp],
        us_ranked=[us_eq, extra_us, etf],
        all_ranked=all_ranked,
    )

    # Diversity proxy: first entry should not be identical across all.
    first_items = {card.next_checks[0] for card in top}
    assert len(first_items) >= 2


def test_counter_evidence_candidate_specific_non_empty() -> None:
    # volume_spike-only candidate should get a volume-related counter line
    us_spike = _candidate_us_equity(volume_spike=True, discovery_score=7)
    ev = build_counter_evidence(us_spike)
    assert len(ev) >= 1
    assert any("出来高" in line for line in ev)


@pytest.fixture
def mini_discovery_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc

    repo = Path(__file__).resolve().parents[1]
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    cfg = repo / "config"
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(
        "invis_alpha_os.config.us_watchlist.load_us_watchlist_tickers",
        lambda *_a, **_k: ["MSFT", "SPY", "TLT", "GLDM"],
    )
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    for sym in ("MSFT", "GLDM"):
        bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / f"{sym}.json")
        save_us_daily_bars_cache(
            sym,
            [dict(b) for b in bars],
            asset_class="us_equity",
            source="local_fixture",
            fetched_at="2026-05-24T12:00:00+00:00",
            generated_at="2026-05-24T12:00:05+00:00",
        )
    return tmp_path


def test_build_weekly_candidate_brief_v0_us_only(mini_discovery_cache: Path) -> None:
    brief = build_weekly_candidate_brief_v0(
        report_date="2026-05-27",
        path_base=mini_discovery_cache,
    )
    md = format_weekly_candidate_brief_v0_markdown(brief)
    assert "MSFT" in md or "（該当なし）" not in md or brief.top_picks
    assert "## マクロ環境" in md


def test_format_copy_only_block() -> None:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import WeeklyCandidateBriefV0

    card = CandidateCard(
        brief_type="top_pick",
        candidate=_candidate(reason="surfaced: near_high"),
        reason="注目理由: 52週高値近辺での反応。",
        counter_evidence=("反証1",),
        next_checks=("確認1", "確認2", "確認3"),
    )
    brief = WeeklyCandidateBriefV0(
        report_date="2026-05-27",
        generated_at_jp="t1",
        generated_at_us="t2",
        jp_scope="jp",
        us_scope="us",
        macro_summary="macro",
        top_picks=[card],
    )
    body = format_weekly_candidate_brief_v0_copy(brief)
    assert body.strip().startswith("<<< COPY FROM HERE >>>")
    assert body.strip().endswith("<<< COPY TO HERE >>>")
    assert "## 今週の深掘り候補 上位5件" in body
    assert "| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |" in body
    assert "## 候補別メモ" in body
    assert "- 反証: 反証1" in body
    assert "- 次確認: 確認1" in body
    assert "Counter evidence" not in body
    assert "Next checks" not in body
    for forbidden in (
        "# 週次候補ブリーフ v0.1",
        "## マクロ環境",
        "## 急騰候補",
        "## 押し目候補",
        "## 付録",
        "surfaced:",
        "rapid_mover",
        "near_high",
    ):
        assert forbidden not in body
    lower = body.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert term not in lower


def test_cli_weekly_candidate_brief_copy(mini_discovery_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.cli.main.ROOT_DIR", mini_discovery_cache)
    r = runner.invoke(
        app,
        ["weekly-candidate-brief", "--format", "copy", "--report-date", "2026-05-27"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    out = r.stdout
    assert out.strip().startswith("<<< COPY FROM HERE >>>")
    assert "<<< COPY TO HERE >>>" in out
    assert "# 週次候補ブリーフ — 2026-05-27" in out
    assert "## マクロ環境" not in out
    assert "## 候補別メモ" in out
    assert "| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |" in out
    assert "Counter evidence" not in out
    assert "Next checks" not in out


def test_cli_weekly_candidate_brief_markdown(mini_discovery_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.cli.main.ROOT_DIR", mini_discovery_cache)
    r = runner.invoke(
        app,
        ["weekly-candidate-brief", "--format", "markdown", "--report-date", "2026-05-27"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "週次候補ブリーフ" in r.stdout


def test_theme_highlights_dedupes_by_symbol(mini_discovery_cache: Path) -> None:
    brief = build_weekly_candidate_brief_v0(
        report_date="2026-05-27",
        path_base=mini_discovery_cache,
    )
    syms = [c.candidate.instrument_id for c in brief.theme_highlights]
    assert len(syms) == len(set(syms))


def test_next_checks_5803_avoid_nand_dram() -> None:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import build_next_checks

    c = _candidate_jp(
        code="5803",
        themes=("memory", "semiconductors", "communications"),
        labels=("rapid_mover_20d", "near_high"),
        categories=("rapid_mover", "near_high_quality_trend"),
        discovery_score=10,
    )
    checks = build_next_checks(c)
    joined = " ".join(checks)
    assert "NAND/DRAM" not in joined
    assert "メモリ/半導体市況" not in joined
    assert "光ファイバー/データセンター需要" in joined


def test_7203_reason_and_checks_not_industrials() -> None:
    from invis_alpha_os.product.weekly_candidate_brief_v0 import build_next_checks

    c = _candidate_jp(
        code="7203",
        themes=("industrials",),
        labels=("rapid_mover_20d", "near_high"),
        categories=("rapid_mover", "near_high_quality_trend"),
        discovery_score=10,
    )
    reason = build_reason_human(c, "top_pick")
    assert "産業設備・受注サイクル" not in reason

    checks = build_next_checks(c)
    joined = " ".join(checks)
    assert "設備投資サイクル" not in joined
    assert "為替（円/ドル）" in joined


def test_cli_invalid_format_exit2() -> None:
    r = runner.invoke(app, ["weekly-candidate-brief", "--format", "xml"])
    assert r.exit_code == 2
