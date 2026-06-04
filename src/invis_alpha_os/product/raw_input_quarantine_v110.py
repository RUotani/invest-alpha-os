"""Source-only raw-input quarantine contract with permanent NO-GO execution gates."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum

from invis_alpha_os.product.validation_issue_taxonomy import normalize_validation_issue_key


class QuarantineSourceKind(str, Enum):
    FIXTURE = "fixture"
    SANITIZED_SAMPLE = "sanitized_sample"
    REDACTED_MANUAL_SNAPSHOT = "redacted_manual_snapshot"
    MANUAL_CONFIRMED_SUMMARY = "manual_confirmed_summary"
    RAW_EXCEL_DECLARED = "raw_excel_declared"
    BROKER_EXPORT_DECLARED = "broker_export_declared"
    UNKNOWN = "unknown"


class QuarantineState(str, Enum):
    ACCEPTED_FIXTURE = "accepted_fixture"
    ACCEPTED_SANITIZED = "accepted_sanitized"
    REVIEW_REQUIRED = "review_required"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    BLOCKED_BY_HARD_GATE = "blocked_by_hard_gate"


@dataclass(frozen=True)
class RawInputQuarantineManifestV110:
    source_kind: QuarantineSourceKind
    declared_unit: str | None = None
    declared_currency: str | None = None
    statement_month: str | None = None
    as_of_date: str | None = None
    owner_scope: str | None = None
    redaction_status: str | None = None
    contains_broker_raw: bool = False
    contains_personal_identifiers: bool = False
    contains_account_numbers: bool = False
    actual_import_requested: bool = False
    cache_write_requested: bool = False
    broker_api_implied: bool = False
    env_secret_required: bool = False
    duplicated_month_risk: bool = False
    data_freshness_unclear: bool = False
    same_point_in_time_unclear: bool = False
    review_notes: tuple[str, ...] = ()
    validation_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class RawInputQuarantineReviewV110:
    quarantine_state: QuarantineState
    source_classification: str
    hard_gate_reasons: tuple[str, ...]
    manual_confirmations_required: tuple[str, ...]
    data_quality_warnings: tuple[str, ...]
    normalized_validation_keys: tuple[str, ...]
    import_allowed: bool
    cache_write_allowed: bool
    next_actions_ja: tuple[str, ...]
    safety_note_ja: str


_SAFE_SOURCES = {
    QuarantineSourceKind.FIXTURE,
    QuarantineSourceKind.SANITIZED_SAMPLE,
    QuarantineSourceKind.REDACTED_MANUAL_SNAPSHOT,
    QuarantineSourceKind.MANUAL_CONFIRMED_SUMMARY,
}


def build_safe_fixture_quarantine_manifest_v110() -> RawInputQuarantineManifestV110:
    return RawInputQuarantineManifestV110(
        source_kind=QuarantineSourceKind.FIXTURE,
        declared_unit="man_yen",
        declared_currency="JPY",
        statement_month="2026-05",
        owner_scope="household",
        redaction_status="redacted",
        review_notes=("source-only fixture manifest; no raw payload",),
    )


def _hard_gate_reasons(manifest: RawInputQuarantineManifestV110) -> tuple[str, ...]:
    reasons: list[str] = []
    if manifest.source_kind is QuarantineSourceKind.RAW_EXCEL_DECLARED:
        reasons.append("raw_excel_declared")
    if manifest.source_kind is QuarantineSourceKind.BROKER_EXPORT_DECLARED or manifest.contains_broker_raw:
        reasons.append("broker_raw_declared")
    if manifest.contains_account_numbers:
        reasons.append("account_numbers_included")
    if manifest.contains_personal_identifiers and manifest.redaction_status != "redacted":
        reasons.append("non_redacted_personal_identifiers")
    if manifest.actual_import_requested:
        reasons.append("actual_import_requested")
    if manifest.cache_write_requested:
        reasons.append("cache_write_requested")
    if manifest.broker_api_implied:
        reasons.append("broker_api_implied")
    if manifest.env_secret_required:
        reasons.append("env_secret_required")
    if manifest.source_kind is QuarantineSourceKind.UNKNOWN and (
        manifest.contains_personal_identifiers or manifest.redaction_status in {None, "unknown", "not_redacted"}
    ):
        reasons.append("unknown_source_sensitive_data_possible")
    return tuple(reasons)


def _manual_confirmations(manifest: RawInputQuarantineManifestV110) -> tuple[str, ...]:
    confirmations: list[str] = []
    if manifest.declared_unit in {None, "unknown"}:
        confirmations.append("declared unitを確認する")
    if manifest.declared_currency in {None, "unknown", "MIXED"}:
        confirmations.append("declared currencyを確認する")
    if manifest.statement_month is None and manifest.as_of_date is None:
        confirmations.append("as-of month/dateを確認する")
    if manifest.owner_scope in {None, "unknown"}:
        confirmations.append("owner scopeを確認する")
    if manifest.redaction_status not in {"redacted"}:
        confirmations.append("redaction statusを確認する")
    return tuple(confirmations)


def _data_quality_warnings(manifest: RawInputQuarantineManifestV110) -> tuple[str, ...]:
    warnings: list[str] = []
    normalized_keys = {normalize_validation_issue_key(key) for key in manifest.validation_keys}
    if "ratio_total_mismatch" in normalized_keys:
        warnings.append("ratio合計不整合")
    if manifest.duplicated_month_risk:
        warnings.append("duplicated month risk")
    if manifest.data_freshness_unclear:
        warnings.append("data freshness unclear")
    if manifest.same_point_in_time_unclear:
        warnings.append("source同一時点性不明")
    return tuple(warnings)


def review_raw_input_quarantine_manifest_v110(
    manifest: RawInputQuarantineManifestV110,
) -> RawInputQuarantineReviewV110:
    """Classify a declaration-only manifest without reading or importing raw input."""

    hard_gate_reasons = _hard_gate_reasons(manifest)
    confirmations = _manual_confirmations(manifest)
    warnings = _data_quality_warnings(manifest)
    if hard_gate_reasons:
        state = QuarantineState.BLOCKED_BY_HARD_GATE
    elif manifest.source_kind not in _SAFE_SOURCES:
        state = QuarantineState.QUARANTINED
    elif confirmations or warnings:
        state = QuarantineState.REVIEW_REQUIRED
    elif manifest.source_kind is QuarantineSourceKind.FIXTURE:
        state = QuarantineState.ACCEPTED_FIXTURE
    else:
        state = QuarantineState.ACCEPTED_SANITIZED
    return RawInputQuarantineReviewV110(
        quarantine_state=state,
        source_classification=manifest.source_kind.value,
        hard_gate_reasons=hard_gate_reasons,
        manual_confirmations_required=confirmations,
        data_quality_warnings=warnings,
        normalized_validation_keys=tuple(
            sorted({normalize_validation_issue_key(key) for key in manifest.validation_keys})
        ),
        import_allowed=False,
        cache_write_allowed=False,
        next_actions_ja=(
            "manifest宣言とmanual confirmationを人間が確認する。",
            "raw payloadを読まず、sanitized/redacted summaryのみでreviewを継続する。",
            "actual import / cache writeは別承認までNO-GOを維持する。",
        ),
        safety_note_ja="このquarantine reviewはsource-onlyであり、raw input読取・actual import・cache writeを実行しません。",
    )


def render_raw_input_quarantine_review_markdown_v110(
    manifest: RawInputQuarantineManifestV110,
    review: RawInputQuarantineReviewV110,
) -> str:
    lines = [
        "# Raw Input Quarantine Review",
        "",
        "## Quarantine Summary",
        f"- state: {review.quarantine_state.value}",
        f"- source: {review.source_classification}",
        "- Import Readiness: NO-GO",
        "- Cache Write Readiness: NO-GO",
        "",
        "## Source Classification",
        f"- unit: {manifest.declared_unit or 'unknown'}",
        f"- currency: {manifest.declared_currency or 'unknown'}",
        f"- statement_month: {manifest.statement_month or 'unknown'}",
        f"- redaction_status: {manifest.redaction_status or 'unknown'}",
        "",
        "## Hard Gate Status",
    ]
    lines.extend(f"- {reason}" for reason in review.hard_gate_reasons or ("none declared",))
    lines.extend(["", "## Manual Confirmations Required"])
    lines.extend(f"- {item}" for item in review.manual_confirmations_required or ("none",))
    lines.extend(["", "## Data Quality Warnings"])
    lines.extend(f"- {item}" for item in review.data_quality_warnings or ("none",))
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in review.next_actions_ja)
    lines.extend(
        [
            "",
            "## Safety Summary",
            f"- {review.safety_note_ja}",
            "- broker API / raw Excel direct parsing: not executed / not approved",
            "- actual import / cache write: not executed / not approved",
            "- trading action / real email send: not executed / not approved",
            "",
        ]
    )
    return "\n".join(lines)


def format_raw_input_quarantine_review_json_v110(
    manifest: RawInputQuarantineManifestV110,
    review: RawInputQuarantineReviewV110,
) -> str:
    payload = {"manifest": asdict(manifest), "review": asdict(review)}
    return json.dumps(payload, ensure_ascii=False, indent=2, default=lambda value: value.value)
