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
    build_weekly_candidate_brief_v0,
    format_weekly_candidate_brief_v0_json,
    format_weekly_candidate_brief_v0_markdown,
    is_pullback_candidate,
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


def test_cli_weekly_candidate_brief_markdown(mini_discovery_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.cli.main.ROOT_DIR", mini_discovery_cache)
    r = runner.invoke(
        app,
        ["weekly-candidate-brief", "--format", "markdown", "--report-date", "2026-05-27"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "週次候補ブリーフ" in r.stdout


def test_cli_invalid_format_exit2() -> None:
    r = runner.invoke(app, ["weekly-candidate-brief", "--format", "xml"])
    assert r.exit_code == 2
