from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reports.chatgpt_context_archive import sync_to_reports_repo
from invis_alpha_os.reports.chatgpt_invest_context_pack import build_chatgpt_context_pack

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
    assert pack.json_payload["language"] == "ja"
    assert pack.json_payload["candidates"][0]["ticker"] == "AAPL"


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
