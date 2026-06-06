from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "weekly_report_delivery_status_and_troubleshooting.md"
DELIVERY_SOURCE = ROOT / "src" / "invis_alpha_os" / "reporting" / "email_delivery.py"

NORMALIZED_STATUSES = (
    "generated",
    "preview_created",
    "sent",
    "delivered",
    "blocked",
    "failed",
)


def _delivery_status_literals() -> set[str]:
    tree = ast.parse(DELIVERY_SOURCE.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in {"dry_run", "sent", "blocked", "failed", "delivered"}
    }


def test_delivery_taxonomy_documents_all_six_normalized_statuses() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "## Delivery Status Taxonomy" in text
    for status in NORMALIZED_STATUSES:
        assert f"`{status}`" in text


def test_sent_is_not_documented_as_delivered_without_inbox_evidence() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "`sent` は送信処理の受付成功" in text
    assert "`delivered` は受信側で到達確認済み" in text
    assert "`sent` やmessage idだけを根拠に `delivered` と記録しない" in text


def test_runtime_status_mapping_preserves_existing_source_contract() -> None:
    statuses = _delivery_status_literals()
    text = DOC.read_text(encoding="utf-8")

    assert {"dry_run", "sent", "blocked", "failed"} <= statuses
    assert "delivered" not in statuses
    assert "`email_delivery_status=dry_run` またはpreview artifactあり | `preview_created`" in text
    assert "`email_delivery_status=sent` | `sent`" in text


def test_troubleshooting_contract_is_secret_safe_and_guardrail_first() -> None:
    text = DOC.read_text(encoding="utf-8")

    for required in (
        "## Guardrail-First Reading Order",
        "Executive Summary",
        "Portfolio Guardrails",
        "Candidate Comparison",
        "Deep Dive Cards",
        "If / Then Decision Rules",
        "## Gmail Delivery Troubleshooting",
        "## Secret Non-Display Contract",
        "secret値、env値、OAuth token、credential JSON本文を表示しない",
        "これは売買指示ではない",
    ):
        assert required in text


def test_docs_only_scope_boundary_excludes_cursor_trial_send_surfaces() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "workflow、`reports-private/trial_send`、Gmail実送信、launchd、runtime source実装を変更しない" in text
