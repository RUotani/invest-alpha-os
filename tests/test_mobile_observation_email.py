"""Mobile-first observation email layout tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.daily_email import build_daily_email_from_bundle
from invis_alpha_os.reports.mobile_observation_email import (
    ObservationEmailCard,
    build_mobile_observation_email,
    compress_symbol_list,
    html_has_forbidden_layout,
    limit_actions,
    text_has_excessive_long_lines,
)
from invis_alpha_os.reports.weekly_observation_email import build_weekly_email_draft

runner = CliRunner()


def test_compress_symbol_list_top_five() -> None:
    syms = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL"]
    assert compress_symbol_list(syms, top_n=5) == "AAPL, MSFT, NVDA, AMZN, META (+2 more)"


def test_limit_actions_max_three_filters_commands() -> None:
    actions = limit_actions(
        [
            "Review repeat symbols in observation log.",
            ".venv/bin/python -m invis_alpha_os.cli.main validate forward-p3-status",
            "Wait for cache horizon maturation.",
            "Another human step.",
        ],
        max_items=3,
    )
    assert len(actions) <= 3
    assert all("venv/bin/python" not in a for a in actions)


def test_mobile_html_has_no_table_or_pre() -> None:
    body = build_mobile_observation_email(
        title="Test Report",
        report_date="2026-05-27",
        disclaimer="Observation only — not buy/sell advice.",
        executive_summary=["Line one.", "Line two."],
        status_cards=[
            ObservationEmailCard("US signals", ("ok: 16/16", "veto: 0")),
        ],
        attention_cards=[
            ObservationEmailCard("Repeat", (f"Top: {compress_symbol_list(['A', 'B', 'C', 'D', 'E', 'F'])}",)),
        ],
        next_actions=["Action one.", "Action two."],
        full_report_attachment_name="sample.md",
    )
    assert not html_has_forbidden_layout(body.html_body)
    assert "<table" not in body.html_body.lower()
    assert "| symbol" not in body.text_body
    assert text_has_excessive_long_lines(body.text_body) is False
    assert body.text_body.count("次の確認事項") == 1
    assert "添付: sample.md" in body.text_body


def test_build_daily_email_mobile_layout(tmp_path: Path) -> None:
    bundle = tmp_path / "2026-05-27"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("stale 0 fresh_enough 16", encoding="utf-8")
    (bundle / "signals_us_cache_preview.md").write_text(
        "| symbol / name | latest_date | freshness_status | close | return_1d | return_5d | return_20d | volume_status | note |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| MSFT | 2026-05-26 | fresh_enough | 100 | +0.1% | +0.2% | +1.0% | ok | |\n",
        encoding="utf-8",
    )
    draft = build_daily_email_from_bundle(bundle)
    assert not html_has_forbidden_layout(draft.html_body)
    assert "## サマリー" in draft.text_body
    assert draft.text_body.count("- ") >= 3


def test_daily_email_dry_run_generates_previews(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "operator_summary.md").write_text("stale 0", encoding="utf-8")
    r = runner.invoke(app, ["daily-email", "--bundle-dir", str(bundle), "--dry-run"])
    assert r.exit_code == 0, r.stdout + r.stderr
    html = (bundle / "email" / "email_preview.html").read_text(encoding="utf-8")
    assert not html_has_forbidden_layout(html)


@pytest.fixture
def mini_us_cache_for_weekly_email(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc
    import invis_alpha_os.product.weekly_us_observation as weekly

    repo = Path(__file__).resolve().parents[1]
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "peer_map.yaml").write_text('peer_map:\n  MSFT:\n    - MSFT\n', encoding="utf-8")
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(config_paths, "CONFIG_DIR", cfg)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(weekly, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(
        "invis_alpha_os.config.us_watchlist.load_us_watchlist_tickers",
        lambda: ["MSFT"],
    )
    monkeypatch.setattr(
        "invis_alpha_os.product.weekly_us_observation.load_us_watchlist_tickers",
        lambda: ["MSFT"],
    )
    from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
    from invis_alpha_os.signals.momentum import load_bars_json_file

    bars = load_bars_json_file(repo / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json")
    save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    monkeypatch.setattr(
        "invis_alpha_os.product.observation_health.build_us_universe_expansion_report",
        lambda **_kw: {"tier_1_missing_refresh_order": []},
    )
    return tmp_path


def test_weekly_email_draft_mobile(mini_us_cache_for_weekly_email: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("invis_alpha_os.cli.main.ROOT_DIR", mini_us_cache_for_weekly_email)
    draft = build_weekly_email_draft(
        path_base=mini_us_cache_for_weekly_email,
        report_date="2026-05-27",
        full_report_path="reports/2026-05-27/sample_weekly_observation_report_v1.md",
    )
    assert not html_has_forbidden_layout(draft.html_body)
    assert "matched_normal" in draft.text_body
    assert "次の確認事項" in draft.text_body
    section = draft.text_body.split("次の確認事項（最大3件）")[-1]
    section = section.split("詳細レポート")[0]
    bullet_lines = [ln for ln in section.splitlines() if ln.startswith("- ")]
    assert len(bullet_lines) <= 3
