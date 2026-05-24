"""Tests for evidence manifest helper."""

from __future__ import annotations

from pathlib import Path

from invis_alpha_os.product.evidence_manifest import (
    build_evidence_manifest,
    write_evidence_manifest_report,
)


def test_build_and_write_evidence_manifest(tmp_path: Path) -> None:
    evidence = tmp_path / "outputs" / "evidence" / "sample.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("# sample evidence\n", encoding="utf-8")

    manifest = build_evidence_manifest(
        task_id="sample_task",
        evidence_path=evidence,
        command="debug us-provider-cache-preview --symbol AMD",
        result="validation_error",
        summary="blocked on provider_api_key_required",
    )
    assert manifest["sha256"]
    assert manifest["size_bytes"] == evidence.stat().st_size
    assert manifest["secret_free"] is True

    out = write_evidence_manifest_report(manifest, path_base=tmp_path, report_date="2026-05-24")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "sample_task" in text
    assert "validation_error" in text
