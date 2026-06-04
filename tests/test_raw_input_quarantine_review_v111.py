from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.portfolio_data_quality_review_v109 import build_portfolio_data_quality_review_v109
from invis_alpha_os.product.raw_input_quarantine_review_v111 import (
    PortfolioQuarantineCrossReviewStateV111,
    build_declared_raw_excel_manifest_fixture_v111,
    build_portfolio_quarantine_cross_review_v111,
    render_portfolio_quarantine_cross_review_markdown_v111,
)
from invis_alpha_os.product.raw_input_quarantine_v110 import (
    build_safe_fixture_quarantine_manifest_v110,
    review_raw_input_quarantine_manifest_v110,
)


def test_v111_safe_fixture_still_requires_manual_review_and_stays_no_go() -> None:
    review = build_portfolio_quarantine_cross_review_v111()
    assert review.cross_review_state is PortfolioQuarantineCrossReviewStateV111.MANUAL_REVIEW_REQUIRED
    assert review.portfolio_quality_severity == "WARN"
    assert review.quarantine_state == "accepted_fixture"
    assert review.import_readiness == "NO-GO"
    assert review.cache_write_readiness == "NO-GO"


def test_v111_declared_raw_excel_is_blocked_without_raw_payload() -> None:
    manifest = build_declared_raw_excel_manifest_fixture_v111()
    review = build_portfolio_quarantine_cross_review_v111(manifest)
    assert review.cross_review_state is PortfolioQuarantineCrossReviewStateV111.BLOCKED_BY_HARD_GATE
    assert review.quarantine_state == "blocked_by_hard_gate"
    assert review.import_readiness == "NO-GO"


def test_v111_maps_portfolio_and_quarantine_keys_through_common_taxonomy() -> None:
    review = build_portfolio_quarantine_cross_review_v111()
    assert "ratio_total_mismatch" in review.shared_validation_keys
    assert "net_worth_mismatch" in review.shared_validation_keys
    assert "cash_below_minimum_guardrail" in review.shared_validation_keys
    assert "target_allocation_gap" not in review.shared_validation_keys


def test_v111_combines_manual_confirmations_without_raw_data() -> None:
    review = build_portfolio_quarantine_cross_review_v111(build_declared_raw_excel_manifest_fixture_v111())
    joined = "\n".join(review.manual_confirmation_items_ja)
    assert "対象月2026-05が最新portfolio inputか確認" in joined
    assert "declared unitを確認" in joined
    assert "owner scopeを確認" in joined


def test_v111_markdown_keeps_cross_report_no_go_semantics() -> None:
    manifest = build_safe_fixture_quarantine_manifest_v110()
    portfolio = build_portfolio_data_quality_review_v109()
    quarantine = review_raw_input_quarantine_manifest_v110(manifest)
    cross = build_portfolio_quarantine_cross_review_v111(manifest)
    markdown = render_portfolio_quarantine_cross_review_markdown_v111(portfolio, quarantine, cross)
    assert "Import Readiness: NO-GO" in markdown
    assert "Cache Write Readiness: NO-GO" in markdown
    assert "actual import / cache write: not executed / not approved" in markdown


def test_v111_cli_supports_safe_and_blocked_fixture_scenarios() -> None:
    runner = CliRunner()
    safe = runner.invoke(app, ["portfolio-quarantine-cross-review", "--scenario", "safe_fixture", "--format", "json"])
    blocked = runner.invoke(
        app,
        ["portfolio-quarantine-cross-review", "--scenario", "raw_excel_declared", "--format", "json"],
    )
    assert safe.exit_code == 0
    assert blocked.exit_code == 0
    assert json.loads(safe.stdout)["cross_review"]["cross_review_state"] == "manual_review_required"
    assert json.loads(blocked.stdout)["cross_review"]["cross_review_state"] == "blocked_by_hard_gate"


def test_v111_cli_rejects_unknown_scenario() -> None:
    result = CliRunner().invoke(app, ["portfolio-quarantine-cross-review", "--scenario", "raw-file-path"])
    assert result.exit_code == 2
    assert "unsupported scenario" in result.stderr


def test_v111_source_has_no_raw_path_or_execution_implementation() -> None:
    text = Path("src/invis_alpha_os/product/raw_input_quarantine_review_v111.py").read_text(encoding="utf-8").lower()
    forbidden = ("open(", "read_text(", "read_bytes(", "pandas", "openpyxl", "requests.", "urllib", "write_text(", "save_", "send_gmail", "order_placement")
    assert all(term not in text for term in forbidden)
