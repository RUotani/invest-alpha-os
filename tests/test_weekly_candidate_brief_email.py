"""Weekly Candidate Brief Gmail preview (dry-run only)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.discovery.cross_market_contract import FORBIDDEN_OUTPUT_TERMS
from invis_alpha_os.reports.weekly_candidate_brief_email import (
    build_weekly_candidate_brief_email_draft,
    build_weekly_candidate_brief_email_subject,
)

runner = CliRunner()
SAMPLE_COPY = """<<< COPY FROM HERE >>>
# Weekly Candidate Brief — 2026-05-27

## 今週の深掘り候補 Top 5

| Rank | Symbol | Name | Market | Type | Short reason |
|---|---|---|---|---|---|
| 1 | 7203 | トヨタ | JP | 注目 | 20日モメンタム継続 |

## 候補別メモ

### 1. 7203 トヨタ
- 反証: 過熱後の反落リスク
- 次確認: 需要と為替の再確認

<<< COPY TO HERE >>>
"""

SAMPLE_COPY_JA_TABLE = """<<< COPY FROM HERE >>>
# 週次候補ブリーフ — 2026-06-02

## 今週の深掘り候補 上位5件

| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |
|---|---|---|---|---|---|
| 1 | 285A | キオクシア | JP | 注目 | 20日モメンタムが強い |

## 候補別メモ

### 1. 285A キオクシア
- 反証: 短期の過熱サイン
- 次確認: NAND/DRAM市況

<<< COPY TO HERE >>>
"""


def test_weekly_candidate_brief_email_subject() -> None:
    assert build_weekly_candidate_brief_email_subject("2026-05-27") == (
        "[TEST][invest-alpha-os] Weekly Candidate Brief 2026-05-27"
    )


def test_weekly_candidate_brief_email_draft_uses_copy_body() -> None:
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-05-27", copy_body=SAMPLE_COPY)
    assert draft.subject.endswith("2026-05-27")
    assert "7203" in draft.text_body
    assert len(draft.text_body) > 800
    assert draft.text_body.startswith("テストメール")
    assert draft.html_body is not None
    assert len(draft.html_body) > 1200
    assert "テストメール" in draft.html_body
    assert "移動平均線の位置づけ" in draft.text_body
    assert "定量スナップショット" in draft.text_body
    assert "モメンタム根拠" in draft.text_body
    assert "反証・下落リスク" in draft.text_body
    assert "情報ソース" in draft.text_body
    assert "次に確認すること" in draft.text_body
    assert "移動平均線の位置づけ" in draft.html_body
    assert "定量スナップショット" in draft.html_body
    assert "モメンタム根拠" in draft.html_body
    assert "反証・下落リスク" in draft.html_body
    assert "情報ソース" in draft.html_body
    assert "次に確認すること" in draft.html_body
    assert "Weekly Observation Report" not in draft.text_body
    lower = draft.text_body.lower()
    for term in FORBIDDEN_OUTPUT_TERMS:
        assert term not in lower


def test_weekly_candidate_brief_email_parses_japanese_copy_ready_table() -> None:
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-02", copy_body=SAMPLE_COPY_JA_TABLE)

    assert "注目候補数: 1" in draft.text_body
    assert "285A" in draft.text_body
    assert "キオクシア" in draft.text_body
    assert "NAND/DRAM市況" in draft.text_body
    assert "強い新規リスク候補: 0件" not in draft.text_body


def test_weekly_candidate_brief_email_dry_run_cli(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text(
        SAMPLE_COPY,
        encoding="utf-8",
    )
    full_md = report_dir / "weekly_candidate_brief_v0_1.md"
    full_md.write_text("# full report\n", encoding="utf-8")

    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--copy-file",
            str(copy_path),
            "--full-md",
            str(full_md),
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert (report_dir / "email" / "email_preview.eml").is_file()
    assert "dry-run only" in r.stdout
    assert "[TEST][invest-alpha-os] Weekly Candidate Brief 2026-05-27" in r.stdout
    txt = (report_dir / "email" / "email_preview.txt").read_text(encoding="utf-8")
    html = (report_dir / "email" / "email_preview.html").read_text(encoding="utf-8")
    assert "テストメール" in txt
    assert "テストメール" in html
    assert "7203" in txt
    assert "移動平均線の位置づけ" in txt
    assert "定量スナップショット" in txt
    assert "反証・下落リスク" in txt


def test_weekly_candidate_brief_email_no_candidate_is_not_empty_report() -> None:
    copy_body = """<<< COPY FROM HERE >>>
# 週次候補ブリーフ — 2026-06-02

## 今週の結論

- 強い新規リスク候補: 0件
- 理由: データ品質・coverage・score条件を同時に満たす候補がありません。
- 判断方針: 現金比率が低い前提で、新規リスク追加より監視・整理・現金回復を優先します。
- 候補パイプライン: 入力3 / coverage不足3 / score未達0 / veto0 / 深掘り可能0
- 主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。
- Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。
- これは実行指示ではなく、根拠補完と安全確認の分類です。
- 候補0件の主因: coverage不足 3件 / score未達 coverage/veto確認を優先 / veto 0件
- 次確認: 価格・出来高・期間・score内訳・veto理由

## 今週の深掘り候補 上位5件

| 順位 | 銘柄 | 名称 | 市場 | 区分 | 短期理由 |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

<<< COPY TO HERE >>>
"""
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-02", copy_body=copy_body)

    assert "注目候補数: 0" in draft.text_body
    assert "強い新規リスク候補: 0件" in draft.text_body
    assert "## 今週の行動チェックリスト" in draft.text_body
    assert "ポートフォリオ前提: 現金11.7% / 個別株19.6% / 株式系67.8%" in draft.text_body
    assert "### 今週やってよいこと" in draft.text_body
    assert "### 今週やらないこと" in draft.text_body
    assert "### 次に確認すること" in draft.text_body
    assert "## 候補パイプライン（短縮）" in draft.text_body
    assert "候補パイプライン: 入力3 / coverage不足3 / score未達0 / veto0 / 深掘り可能0" in draft.text_body
    assert "主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。" in draft.text_body
    assert "## Score / Veto（短縮）" in draft.text_body
    assert "Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in draft.text_body
    assert "これは実行指示ではなく、根拠補完と安全確認の分類です。" in draft.text_body
    assert "候補0件の理由、coverage不足、score未達、veto理由を確認する" in draft.text_body
    assert "候補0件の主因: coverage不足 3件 / score未達 coverage/veto確認を優先 / veto 0件" in draft.text_body
    assert "次確認: 価格・出来高・期間・score内訳・veto理由" in draft.text_body
    assert "veto該当0件でも、直ちに新規追加判断には進まず、coverage/scoreの再確認を優先します。" in draft.text_body
    assert "不足 790.2万円" in draft.text_body
    assert "上回り +813.8万円" in draft.text_body
    assert "不足 151.9万円" in draft.text_body
    assert "根拠不足の新規個別株・高ベータ枠を追加しない" in draft.text_body
    assert "株式系67.8%と個別株19.6%に重複リスク" in draft.text_body
    assert "## 整理・監視優先度" in draft.text_body
    assert "このスコアは売却指示ではなく、次に確認すべき整理・監視優先度です" in draft.text_body
    assert "個別株枠: 4 / 5" in draft.text_body
    assert "株式系重複リスク: 4 / 5" in draft.text_body
    assert "高ボラ枠: 3 / 5" in draft.text_body
    assert "データ不足候補: 3 / 5" in draft.text_body
    assert "候補0件はレポート失敗ではありません" in draft.text_body
    assert "no candidates in copy body" not in draft.text_body
    assert draft.html_body is not None
    assert "強い新規リスク候補: 0件" in draft.html_body
    assert "今週の行動チェックリスト" in draft.html_body
    assert "今週やってよいこと" in draft.html_body
    assert "今週やらないこと" in draft.html_body
    assert "次に確認すること" in draft.html_body
    assert "候補パイプライン（短縮）" in draft.html_body
    assert "候補パイプライン: 入力3 / coverage不足3 / score未達0 / veto0 / 深掘り可能0" in draft.html_body
    assert "主因: coverage不足。次確認: 価格・出来高・期間・score内訳・veto理由。" in draft.html_body
    assert "Score / Veto（短縮）" in draft.html_body
    assert "Score/Veto: 深掘り候補0 / 監視2 / veto確認2 / score補完0 / 高優先レビュー1。" in draft.html_body
    assert "これは実行指示ではなく、根拠補完と安全確認の分類です。" in draft.html_body
    assert "候補0件の主因: coverage不足 3件 / score未達 coverage/veto確認を優先 / veto 0件" in draft.html_body
    assert "次確認: 価格・出来高・期間・score内訳・veto理由" in draft.html_body
    assert "veto該当0件でも、直ちに新規追加判断には進まず、coverage/scoreの再確認を優先します。" in draft.html_body
    assert "現金11.7% / 個別株19.6% / 株式系67.8%" in draft.html_body
    assert "不足 790.2万円" in draft.html_body
    assert "上回り +813.8万円" in draft.html_body
    assert "不足 151.9万円" in draft.html_body
    assert "整理・監視優先度" in draft.html_body
    assert "個別株枠: 4 / 5" in draft.html_body
    assert "株式系重複リスク: 4 / 5" in draft.html_body
    assert "no candidates in copy body" not in draft.html_body
    assert "| 順位 |" not in draft.html_body


def test_weekly_candidate_brief_email_action_checklist_always_shown() -> None:
    draft = build_weekly_candidate_brief_email_draft(report_date="2026-06-02", copy_body=SAMPLE_COPY)

    assert "## 今週の行動チェックリスト" in draft.text_body
    assert "根拠不足の新規個別株・高ベータ枠を追加しない" in draft.text_body
    assert "## 整理・監視優先度" in draft.text_body
    assert draft.html_body is not None
    assert "今週の行動チェックリスト" in draft.html_body
    assert "整理・監視優先度" in draft.html_body
    assert "候補0件はレポート失敗ではなく" in draft.html_body


def test_weekly_candidate_brief_email_missing_copy_exit2(tmp_path: Path) -> None:
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(tmp_path),
        ],
    )
    assert r.exit_code == 2


def test_weekly_candidate_brief_email_send_test_requires_gate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("GMAIL_TO", "tester@example.com")
    monkeypatch.delenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", raising=False)
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 2
    assert "test send blocked" in r.stderr


def test_weekly_candidate_brief_email_send_test_requires_gmail_to(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "1")
    monkeypatch.delenv("GMAIL_TO", raising=False)
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 2
    assert "GMAIL_TO is required" in r.stderr


def test_weekly_candidate_brief_email_send_test_blocks_recipient_not_in_allowlist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "1")
    monkeypatch.setenv("CONFIRM_GMAIL_SEND", "YES")
    monkeypatch.setenv("GMAIL_TO", "other@example.com")
    monkeypatch.setenv("GMAIL_SELF_EMAIL", "self@example.com")
    monkeypatch.setenv("GMAIL_REPORT_FROM", "sender@example.com")
    monkeypatch.setattr("invis_alpha_os.cli.main.credentials_configured", lambda: True)
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 2
    assert "gmail_send_gate_recipient" in r.stderr


def test_weekly_candidate_brief_email_send_test_sends_when_gated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report_dir = tmp_path / "reports" / "2026-05-27"
    report_dir.mkdir(parents=True)
    copy_path = report_dir / "weekly_candidate_brief_copy.md"
    copy_path.write_text("# brief\n", encoding="utf-8")
    monkeypatch.setenv("INVEST_ALPHA_OS_ALLOW_GMAIL_TEST_SEND", "1")
    monkeypatch.setenv("CONFIRM_GMAIL_SEND", "YES")
    monkeypatch.setenv("GMAIL_TO", "tester@example.com")
    monkeypatch.setenv("GMAIL_SELF_EMAIL", "tester@example.com")
    monkeypatch.setenv("GMAIL_REPORT_FROM", "sender@example.com")
    monkeypatch.setattr("invis_alpha_os.cli.main.credentials_configured", lambda: True)
    monkeypatch.setattr(
        "invis_alpha_os.cli.main.send_gmail_message",
        lambda raw, allow_interactive_oauth=False: {"id": "test-id-1"},
    )
    r = runner.invoke(
        app,
        [
            "weekly-candidate-brief-email",
            "--report-date",
            "2026-05-27",
            "--report-dir",
            str(report_dir),
            "--send-test",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "sent test message id='test-id-1'" in r.stdout
