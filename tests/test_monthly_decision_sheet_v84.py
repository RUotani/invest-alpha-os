from __future__ import annotations

from invis_alpha_os.portfolio.monthly_decision_sheet_v84 import (
    FORBIDDEN_DECISION_SHEET_PHRASES_V84,
    build_monthly_decision_sheet_v84_markdown,
    default_monthly_decision_sheet_input_v84,
)


def test_monthly_decision_sheet_v84_contains_required_sections() -> None:
    md = build_monthly_decision_sheet_v84_markdown()

    assert "# Monthly Decision Sheet" in md
    assert "## 今月の結論" in md
    assert "## 判断サマリー" in md
    assert "## 今月の意思決定テーブル" in md
    assert "## 現金回復ステップ" in md
    assert "## 次月への持ち越し" in md
    assert "## Safety note" in md
    assert "| 判断領域 | 月次スタンス | 理由 | 次に確認すること |" in md


def test_monthly_decision_sheet_v84_includes_required_numbers_and_gap_values() -> None:
    md = build_monthly_decision_sheet_v84_markdown()

    assert "4327.9万円" in md
    assert "508.2万円 / 11.7%" in md
    assert "2934.5万円 / 67.8%" in md
    assert "846.3万円 / 19.6%" in md

    assert "あと 141.0万円" in md
    assert "あと 357.4万円" in md
    assert "あと 790.2万円" in md

    assert "overweight +813.8万円" in md
    assert "above band +4.6% / +197.1万円" in md
    assert "above target +128.3万円" in md
    assert "below target 151.9万円不足" in md


def test_monthly_decision_sheet_v84_contains_safety_wording() -> None:
    md = build_monthly_decision_sheet_v84_markdown()
    assert "このシートは売買指示ではなく" in md
    assert "確認・記録・リスク管理のための分類" in md
    assert "価格、税金、NISA枠、取得単価、家計キャッシュフロー、リスク許容度を別途確認して判断" in md


def test_monthly_decision_sheet_v84_does_not_include_forbidden_phrases() -> None:
    md = build_monthly_decision_sheet_v84_markdown()
    for phrase in FORBIDDEN_DECISION_SHEET_PHRASES_V84:
        assert phrase not in md


def test_monthly_decision_sheet_v84_uses_neutralized_decision_labels() -> None:
    md = build_monthly_decision_sheet_v84_markdown()

    assert "新規個別株リスク" in md
    assert "インデックス積立方針" in md
    assert "債券ポジション" in md
    assert "オルタナティブ配分" in md
    assert "現金回復" in md
    assert "既存ポジション確認" in md

    assert "買う（新規個別株追加）" not in md
    assert "保留（インデックス積立）" not in md
    assert "保留（債券追加）" not in md
    assert "保留（GOLD/オルタナ追加）" not in md
    assert "| アクション | 判定 | 理由 | 次に確認すること |" not in md


def test_monthly_decision_sheet_v84_default_input_snapshot_values() -> None:
    snapshot = default_monthly_decision_sheet_input_v84()
    assert snapshot.total_assets_10k_yen == 4327.9
    assert snapshot.cash_10k_yen == 508.2
    assert snapshot.equity_total_10k_yen == 2934.5
    assert snapshot.individual_stocks_10k_yen == 846.3
    assert snapshot.bonds_10k_yen == 582.7
    assert snapshot.temporary_alternatives_10k_yen == 302.5

