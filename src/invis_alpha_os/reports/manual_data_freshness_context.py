"""Integrate manual data freshness signals into context pack and cache readiness."""

from __future__ import annotations

from typing import Any


def build_manual_freshness_context_block(pipeline: dict[str, Any]) -> dict[str, Any]:
    discovery = pipeline.get("discovery") or {}
    schema = pipeline.get("schema_validation") or {}
    dry_run = pipeline.get("import_flow_dry_run") or {}
    assistant = pipeline.get("export_assistant") or {}
    return {
        "manual_data_detected": bool(discovery.get("manual_file_detected")),
        "schema_status": schema.get("overall_status", "not_run"),
        "schema_valid": bool(schema.get("schema_valid")),
        "prohibited_columns_detected": bool(schema.get("prohibited_columns_detected")),
        "target_ticker_coverage": schema.get("target_ticker_coverage", []),
        "freshness_gap_before": "see_candidate_freshness_classification",
        "freshness_gap_after_expected": dry_run.get("expected_freshness_improvement", "unknown"),
        "actual_import_gate_status": dry_run.get("actual_import_gate_status", "pending_user_approval"),
        "dry_run_status": dry_run.get("dry_run_status", "not_run"),
        "export_assistant_generated": bool(assistant.get("template_generated")),
        "next_action": pipeline.get("next_action", "review_manual_data_pipeline"),
        "solo_approval_requirement_waived": None,
    }


def apply_manual_freshness_to_context(context_payload: dict[str, Any], pipeline: dict[str, Any]) -> dict[str, Any]:
    out = dict(context_payload)
    block = build_manual_freshness_context_block(pipeline)
    out["manual_data_freshness"] = block
    notes = list(out.get("notes") or []) if isinstance(out.get("notes"), list) else []
    if not block["manual_data_detected"]:
        notes.append("manual JP bars file not detected; export assistant available")
    elif not block["schema_valid"]:
        notes.append("manual JP bars file detected but schema validation not pass")
    elif block["dry_run_status"] == "pass":
        notes.append("manual JP bars dry-run import flow pass; actual import still gated")
    out["notes"] = notes
    return out


def apply_manual_freshness_to_cache_readiness(
    readiness_payload: dict[str, Any],
    pipeline: dict[str, Any],
) -> dict[str, Any]:
    out = dict(readiness_payload)
    block = build_manual_freshness_context_block(pipeline)
    out["manual_data_freshness"] = block
    notes = list(out.get("notes") or [])
    if not block["manual_data_detected"]:
        notes.append("Manual data required: place manual_jp_bars.csv on Desktop/Downloads")
    elif block["actual_import_gate_status"] == "pending_user_approval":
        notes.append("Manual data dry-run complete; await explicit actual import approval")
    out["notes"] = notes
    out["manual_data_required"] = not block["manual_data_detected"]
    return out
