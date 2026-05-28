from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_context_archive import (
    sync_to_reports_repo,
    sync_validation_outputs_to_reports_repo,
)
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack
from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import CandidateQuantMetrics

runner = CliRunner()


def _write_weekly_json(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "weekly_candidate_brief.v0.1",
        "report_date": "2026-05-27",
        "sections": {
            "top_picks": [
                {
                    "brief_type": "top_pick",
                    "reason": "注目理由: 20日モメンタムが強い。",
                    "counter_evidence": ["反証サンプル"],
                    "next_checks": ["次確認サンプル"],
                    "candidate": {
                        "instrument_id": "AAPL",
                        "display_name": "AAPL Apple",
                        "market": "US",
                        "themes": ["us_equity"],
                    },
                }
            ],
            "rapid_movers": [],
            "pullbacks": [],
            "avoid": [],
            "insufficient": [],
        },
    }
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_build_chatgpt_context_pack(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    pack = build_chatgpt_context_pack(report_date="2026-05-27", report_dir=report_dir)
    assert "ChatGPT投資対話用Context Pack" in pack.markdown_text
    assert "注目候補Top10" in pack.markdown_text
    assert "AAPL" in pack.markdown_text
    assert "候補分類" in pack.markdown_text
    assert "タイミング分類" in pack.markdown_text
    assert "市場レジーム" in pack.markdown_text
    assert pack.json_payload["language"] == "ja"
    assert pack.json_payload["candidates"][0]["ticker"] == "AAPL"
    assert pack.json_payload["market_regime"]["label"] != "未実装"


def test_cli_context_pack_writes_latest_and_archive(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-context",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert (out_dir / "latest" / "chatgpt_invest_context_pack.md").is_file()
    assert (
        out_dir / "archive" / "2026" / "2026-05-27" / "chatgpt_invest_context_pack.json"
    ).is_file()


def test_sync_reports_repo_rejects_same_repo_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    try:
        sync_to_reports_repo(
            reports_repo_path=repo_root,
            repo_root=repo_root,
            report_date="2026-05-27",
            markdown_text="# test\n",
            json_payload={"ok": True},
        )
    except ValueError as e:
        assert "同一" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_cli_chatgpt_audit_writes_quality_feedback_seed(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    r1 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-context",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r1.exit_code == 0, r1.stdout + r1.stderr

    r2 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-audit",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--write-latest",
            "--write-archive",
            "--write-feedback-template",
            "--write-validation-seed",
        ],
    )
    assert r2.exit_code == 0, r2.stdout + r2.stderr
    assert (out_dir / "latest" / "context_pack_quality_audit.md").is_file()
    assert (out_dir / "latest" / "decision_feedback_template.md").is_file()
    assert (out_dir / "archive" / "2026" / "2026-05-27" / "context_pack_quality_audit.md").is_file()
    assert (out_dir / "validation" / "seeds" / "2026" / "2026-05-27" / "decision_seed.json").is_file()


def test_cli_chatgpt_enrich_and_validation_seed(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    r1 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-context",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r1.exit_code == 0, r1.stdout + r1.stderr
    r2 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-enrich",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r2.exit_code == 0, r2.stdout + r2.stderr
    assert (out_dir / "latest" / "trap_analysis.md").is_file()
    assert (out_dir / "latest" / "trap_analysis.json").is_file()
    context_md = (out_dir / "latest" / "chatgpt_invest_context_pack.md").read_text(encoding="utf-8")
    assert "今週の結論" in context_md
    r3 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-validation-seed",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir / "validation"),
            "--context-json",
            str(out_dir / "latest" / "chatgpt_invest_context_pack.json"),
        ],
    )
    assert r3.exit_code == 0, r3.stdout + r3.stderr
    assert (out_dir / "validation" / "seeds" / "2026" / "2026-05-27" / "decision_seed.json").is_file()


def test_cli_validation_evaluate_writes_dashboard(tmp_path: Path) -> None:
    seeds_dir = tmp_path / "outputs" / "chatgpt_context" / "validation" / "seeds" / "2026" / "2026-05-27"
    seeds_dir.mkdir(parents=True, exist_ok=True)
    seed_payload = {
        "report_date": "2026-05-27",
        "candidates": [
            {
                "ticker": "NOFILE",
                "market": "US",
                "latest_close_at_report": 100.0,
                "classification": "見送り",
                "timing": "見送り",
                "future_evaluation_dates": {"plus_4w": "2026-06-24", "plus_12w": "2026-08-19", "plus_26w": "2026-11-25"},
            }
        ],
    }
    (seeds_dir / "decision_seed.json").write_text(json.dumps(seed_payload, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "outputs" / "chatgpt_context" / "validation" / "results"
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-validation-evaluate",
            "--as-of-date",
            "2026-12-01",
            "--seeds-dir",
            str(tmp_path / "outputs" / "chatgpt_context" / "validation" / "seeds"),
            "--out-dir",
            str(out_dir),
            "--write-dashboard",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert (out_dir / "validation_dashboard.md").is_file()
    assert (out_dir / "validation_dashboard.json").is_file()


def test_sync_validation_outputs_avoids_double_results_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "source_repo"
    repo_root.mkdir()
    reports_repo = tmp_path / "reports_repo"
    reports_repo.mkdir()
    validation_results = tmp_path / "outputs" / "chatgpt_context" / "validation" / "results"
    nested = validation_results / "results" / "2026" / "2026-05-28"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "result_4w.json").write_text('{"ok":true}', encoding="utf-8")

    sync_validation_outputs_to_reports_repo(
        reports_repo_path=reports_repo,
        repo_root=repo_root,
        validation_results_dir=validation_results,
        dashboard_markdown="# dashboard\n",
        dashboard_json_payload={"ok": True},
    )

    assert (reports_repo / "validation" / "results" / "2026" / "2026-05-28" / "result_4w.json").is_file()
    assert not (reports_repo / "validation" / "results" / "results").exists()


def test_build_chatgpt_context_pack_normalizes_top_pick_skip_overheat(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "weekly_candidate_brief.v0.1",
        "report_date": "2026-05-27",
        "sections": {
            "top_picks": [
                {
                    "brief_type": "top_pick",
                    "reason": "急伸中",
                    "counter_evidence": ["過熱リスク"],
                    "next_checks": ["押し目形成確認"],
                    "candidate": {
                        "instrument_id": "5801",
                        "display_name": "5801 古河電工",
                        "market": "jp",
                        "themes": ["energy"],
                    },
                }
            ],
            "rapid_movers": [],
            "pullbacks": [],
            "avoid": [
                {
                    "candidate": {"instrument_id": "5801"},
                }
            ],
            "insufficient": [],
        },
    }
    (report_dir / "weekly_candidate_brief_v0_1.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    monkeypatch.setattr(
        "invis_alpha_os.reports.chatgpt_invest_context_pack.compute_candidate_quant_metrics",
        lambda **_: CandidateQuantMetrics(
        symbol="5801",
        source="cache:test",
        latest_bar_date="2026-05-27",
        latest_close=1000.0,
        ret_5d_pct=0.12,
        ret_20d_pct=0.97,
        ret_60d_pct=1.04,
        ma_25=900.0,
        ma_75=800.0,
        ma_200=700.0,
        dist_ma_25_pct=0.2,
        dist_ma_75_pct=0.25,
        dist_ma_200_pct=0.4,
        high_52w=1100.0,
        low_52w=500.0,
        dist_52w_high_pct=-0.09,
        dist_52w_low_pct=1.0,
        latest_volume=100.0,
        avg_volume_20d=100.0,
        volume_ratio_20d=1.0,
        freshness_label="最新圏",
        missing_reason=None,
        freshness_classification="fresh",
        stale_days=0,
        freshness_reason="直近データが0日差で最新圏",
        timing_impact="通常のタイミング判断が可能。",
    ),
    )
    pack = build_chatgpt_context_pack(report_date="2026-05-27", report_dir=report_dir)
    c0 = pack.json_payload["candidates"][0]
    assert c0["classification"] == "top_pick"
    assert c0["timing"] in {"wait_for_pullback", "overheated_watch"}


def test_priority_queue_includes_data_update_required_warning(tmp_path: Path, monkeypatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    monkeypatch.setattr(
        "invis_alpha_os.reports.chatgpt_invest_context_pack.compute_candidate_quant_metrics",
        lambda **_: CandidateQuantMetrics(
            symbol="AAPL",
            source="cache:test",
            latest_bar_date="2026-01-01",
            latest_close=1000.0,
            ret_5d_pct=0.01,
            ret_20d_pct=0.02,
            ret_60d_pct=0.03,
            ma_25=900.0,
            ma_75=800.0,
            ma_200=700.0,
            dist_ma_25_pct=0.1,
            dist_ma_75_pct=0.1,
            dist_ma_200_pct=0.1,
            high_52w=1100.0,
            low_52w=500.0,
            dist_52w_high_pct=-0.1,
            dist_52w_low_pct=1.0,
            latest_volume=100.0,
            avg_volume_20d=100.0,
            volume_ratio_20d=1.0,
            freshness_label="要更新（直近データが7日超過: 99日）",
            missing_reason=None,
            freshness_classification="data_update_required",
            stale_days=99,
            freshness_reason="直近データが99日古い",
            timing_impact="実タイミング判断不可。テーマ深掘りのみ可。",
        ),
    )
    pack = build_chatgpt_context_pack(report_date="2026-05-27", report_dir=report_dir)
    queue = pack.json_payload["research_queue"]["data_update_required"]
    assert queue and queue[0]["ticker"] == "AAPL"


def test_cli_cache_refresh_readiness_writes_outputs(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    r1 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-context",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r1.exit_code == 0, r1.stdout + r1.stderr
    r2 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-readiness",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--context-json",
            str(out_dir / "latest" / "chatgpt_invest_context_pack.json"),
        ],
    )
    assert r2.exit_code == 0, r2.stdout + r2.stderr
    assert (out_dir / "latest" / "cache_refresh_readiness.md").is_file()
    assert (out_dir / "latest" / "cache_refresh_readiness.json").is_file()


def test_cli_cache_refresh_plan_writes_outputs(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    r1 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-context",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r1.exit_code == 0, r1.stdout + r1.stderr
    r2 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-readiness",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r2.exit_code == 0, r2.stdout + r2.stderr
    r3 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-plan",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--readiness-json",
            str(out_dir / "latest" / "cache_refresh_readiness.json"),
        ],
    )
    assert r3.exit_code == 0, r3.stdout + r3.stderr
    assert (out_dir / "latest" / "cache_refresh_execution_plan.md").is_file()
    assert (out_dir / "latest" / "cache_refresh_execution_plan.json").is_file()


def test_cli_cache_refresh_execute_writes_outputs_and_rejects_execute(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    _write_weekly_json(report_dir)
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    r1 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-chatgpt-context",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r1.exit_code == 0, r1.stdout + r1.stderr
    r2 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-readiness",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
        ],
    )
    assert r2.exit_code == 0, r2.stdout + r2.stderr
    r3 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-plan",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--readiness-json",
            str(out_dir / "latest" / "cache_refresh_readiness.json"),
        ],
    )
    assert r3.exit_code == 0, r3.stdout + r3.stderr
    r4 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-execute",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--plan-json",
            str(out_dir / "latest" / "cache_refresh_execution_plan.json"),
        ],
    )
    assert r4.exit_code == 0, r4.stdout + r4.stderr
    assert (out_dir / "latest" / "cache_refresh_execute_dry_run.md").is_file()
    assert (out_dir / "latest" / "cache_refresh_execute_dry_run.json").is_file()
    r5 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-cache-refresh-execute",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--plan-json",
            str(out_dir / "latest" / "cache_refresh_execution_plan.json"),
            "--execute-refresh",
        ],
    )
    assert r5.exit_code == 2, r5.stdout + r5.stderr
    assert "actual_refresh_not_enabled" in (r5.stdout + r5.stderr)


def test_cli_jp_cache_refresh_dry_run_filters_jquants_high(tmp_path: Path) -> None:
    out_dir = tmp_path / "outputs" / "chatgpt_context"
    (out_dir / "latest").mkdir(parents=True, exist_ok=True)
    (out_dir / "latest" / "cache_refresh_execution_plan.json").write_text(
        json.dumps(
            {
                "targets": [
                    {"ticker": "5802", "provider": "jquants", "priority": "high"},
                    {"ticker": "6645", "provider": "jquants", "priority": "high"},
                    {"ticker": "5801", "provider": "jquants", "priority": "high"},
                    {"ticker": "QQQ", "provider": "us_daily_bars", "priority": "medium"},
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    r4 = runner.invoke(
        app,
        [
            "weekly-candidate-brief-jp-cache-refresh-dry-run",
            "--report-date",
            "2026-05-27",
            "--out-dir",
            str(out_dir),
            "--plan-json",
            str(out_dir / "latest" / "cache_refresh_execution_plan.json"),
        ],
    )
    assert r4.exit_code == 0, r4.stdout + r4.stderr
    md = (out_dir / "latest" / "jp_cache_refresh_dry_run.md").read_text(encoding="utf-8")
    assert "5802" in md and "6645" in md and "5801" in md
    assert "QQQ" not in md
