from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.raw_input_quarantine_v110 import (
    QuarantineSourceKind,
    QuarantineState,
    RawInputQuarantineManifestV110,
    build_safe_fixture_quarantine_manifest_v110,
    format_raw_input_quarantine_review_json_v110,
    render_raw_input_quarantine_review_markdown_v110,
    review_raw_input_quarantine_manifest_v110,
)


def test_v110_accepts_safe_fixture_but_never_allows_import_or_cache() -> None:
    manifest = build_safe_fixture_quarantine_manifest_v110()
    review = review_raw_input_quarantine_manifest_v110(manifest)
    assert review.quarantine_state is QuarantineState.ACCEPTED_FIXTURE
    assert review.import_allowed is False
    assert review.cache_write_allowed is False


def test_v110_requires_review_for_missing_metadata_and_quality_warnings() -> None:
    manifest = RawInputQuarantineManifestV110(
        source_kind=QuarantineSourceKind.SANITIZED_SAMPLE,
        declared_unit="unknown",
        declared_currency="unknown",
        owner_scope="unknown",
        redaction_status="redacted",
        duplicated_month_risk=True,
        data_freshness_unclear=True,
        same_point_in_time_unclear=True,
        validation_keys=("allocation_ratio_total_mismatch",),
    )
    review = review_raw_input_quarantine_manifest_v110(manifest)
    assert review.quarantine_state is QuarantineState.REVIEW_REQUIRED
    assert "ratio_total_mismatch" in review.normalized_validation_keys
    assert "ratio合計不整合" in review.data_quality_warnings
    assert len(review.manual_confirmations_required) >= 4


def test_v110_blocks_declared_raw_broker_sensitive_and_execution_requests() -> None:
    manifest = RawInputQuarantineManifestV110(
        source_kind=QuarantineSourceKind.RAW_EXCEL_DECLARED,
        contains_broker_raw=True,
        contains_personal_identifiers=True,
        contains_account_numbers=True,
        redaction_status="not_redacted",
        actual_import_requested=True,
        cache_write_requested=True,
        broker_api_implied=True,
        env_secret_required=True,
    )
    review = review_raw_input_quarantine_manifest_v110(manifest)
    assert review.quarantine_state is QuarantineState.BLOCKED_BY_HARD_GATE
    assert {
        "raw_excel_declared",
        "broker_raw_declared",
        "account_numbers_included",
        "non_redacted_personal_identifiers",
        "actual_import_requested",
        "cache_write_requested",
        "broker_api_implied",
        "env_secret_required",
    }.issubset(review.hard_gate_reasons)
    assert not review.import_allowed
    assert not review.cache_write_allowed


def test_v110_unknown_sensitive_source_is_blocked() -> None:
    review = review_raw_input_quarantine_manifest_v110(
        RawInputQuarantineManifestV110(
            source_kind=QuarantineSourceKind.UNKNOWN,
            contains_personal_identifiers=True,
            redaction_status="unknown",
        )
    )
    assert review.quarantine_state is QuarantineState.BLOCKED_BY_HARD_GATE
    assert "unknown_source_sensitive_data_possible" in review.hard_gate_reasons


def test_v110_markdown_and_json_keep_no_go_semantics() -> None:
    manifest = build_safe_fixture_quarantine_manifest_v110()
    review = review_raw_input_quarantine_manifest_v110(manifest)
    markdown = render_raw_input_quarantine_review_markdown_v110(manifest, review)
    payload = json.loads(format_raw_input_quarantine_review_json_v110(manifest, review))
    assert "Import Readiness: NO-GO" in markdown
    assert "Cache Write Readiness: NO-GO" in markdown
    assert payload["review"]["import_allowed"] is False
    assert payload["review"]["cache_write_allowed"] is False


def test_v110_cli_is_manifest_only_and_blocks_execution_flags() -> None:
    result = CliRunner().invoke(
        app,
        [
            "raw-input-quarantine-review",
            "--source-kind",
            "raw_excel_declared",
            "--actual-import-requested",
            "--cache-write-requested",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["review"]["quarantine_state"] == "blocked_by_hard_gate"
    assert payload["review"]["import_allowed"] is False
    assert payload["review"]["cache_write_allowed"] is False


def test_v110_cli_rejects_unknown_source_kind() -> None:
    result = CliRunner().invoke(app, ["raw-input-quarantine-review", "--source-kind", "not-a-kind"])
    assert result.exit_code == 2
    assert "unsupported source kind" in result.stderr


def test_v110_source_has_no_raw_path_or_forbidden_execution_implementation() -> None:
    text = Path("src/invis_alpha_os/product/raw_input_quarantine_v110.py").read_text(encoding="utf-8").lower()
    forbidden = ("open(", "read_text(", "read_bytes(", "pandas", "openpyxl", "requests.", "urllib", "save_", "write_text(", "send_gmail", "order_placement")
    assert all(term not in text for term in forbidden)
