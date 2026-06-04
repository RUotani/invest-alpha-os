"""Cross-review skeleton joining v109 data quality and v110 quarantine declarations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum

from invis_alpha_os.product.portfolio_data_quality_review_v109 import (
    PortfolioDataQualityReviewV109,
    build_portfolio_data_quality_review_v109,
)
from invis_alpha_os.product.raw_input_quarantine_v110 import (
    QuarantineSourceKind,
    QuarantineState,
    RawInputQuarantineManifestV110,
    RawInputQuarantineReviewV110,
    build_safe_fixture_quarantine_manifest_v110,
    review_raw_input_quarantine_manifest_v110,
)
from invis_alpha_os.product.validation_issue_taxonomy import (
    is_known_validation_issue_key,
    normalize_validation_issue_key,
)


class PortfolioQuarantineCrossReviewStateV111(str, Enum):
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    BLOCKED_BY_HARD_GATE = "blocked_by_hard_gate"


@dataclass(frozen=True)
class PortfolioQuarantineCrossReviewV111:
    cross_review_state: PortfolioQuarantineCrossReviewStateV111
    source_classification: str
    portfolio_quality_severity: str
    quarantine_state: str
    shared_validation_keys: tuple[str, ...]
    manual_confirmation_items_ja: tuple[str, ...]
    import_readiness: str
    cache_write_readiness: str
    next_actions_ja: tuple[str, ...]
    safety_note_ja: str


def build_declared_raw_excel_manifest_fixture_v111() -> RawInputQuarantineManifestV110:
    """Return a declaration-only blocked scenario with no raw payload or identifiers."""

    return RawInputQuarantineManifestV110(
        source_kind=QuarantineSourceKind.RAW_EXCEL_DECLARED,
        declared_unit="unknown",
        declared_currency="unknown",
        owner_scope="unknown",
        redaction_status="unknown",
        review_notes=("declaration-only blocked scenario; no raw file or payload",),
    )


def build_portfolio_quarantine_cross_review_v111(
    manifest: RawInputQuarantineManifestV110 | None = None,
) -> PortfolioQuarantineCrossReviewV111:
    source = manifest or build_safe_fixture_quarantine_manifest_v110()
    portfolio_review = build_portfolio_data_quality_review_v109()
    quarantine_review = review_raw_input_quarantine_manifest_v110(source)
    state = (
        PortfolioQuarantineCrossReviewStateV111.BLOCKED_BY_HARD_GATE
        if quarantine_review.quarantine_state is QuarantineState.BLOCKED_BY_HARD_GATE
        else PortfolioQuarantineCrossReviewStateV111.MANUAL_REVIEW_REQUIRED
    )
    shared_keys = tuple(
        sorted(
            key
            for key in {
                *(normalize_validation_issue_key(item.key) for item in portfolio_review.review_items),
                *quarantine_review.normalized_validation_keys,
            }
            if is_known_validation_issue_key(key)
        )
    )
    manual_items = tuple(
        dict.fromkeys(
            (
                *portfolio_review.manual_confirmation_items_ja,
                *quarantine_review.manual_confirmations_required,
            )
        )
    )
    return PortfolioQuarantineCrossReviewV111(
        cross_review_state=state,
        source_classification=quarantine_review.source_classification,
        portfolio_quality_severity=portfolio_review.overall_severity,
        quarantine_state=quarantine_review.quarantine_state.value,
        shared_validation_keys=shared_keys,
        manual_confirmation_items_ja=manual_items,
        import_readiness="NO-GO",
        cache_write_readiness="NO-GO",
        next_actions_ja=(
            "portfolio data quality warningとquarantine宣言を人間が横断確認する。",
            "raw payloadを読まず、sanitized/redacted declarationのみを維持する。",
            "actual import / cache writeは別承認までNO-GOを維持する。",
        ),
        safety_note_ja="cross-reviewはsource-only skeletonであり、raw parsing・actual import・cache writeを実行しません。",
    )


def render_portfolio_quarantine_cross_review_markdown_v111(
    portfolio_review: PortfolioDataQualityReviewV109,
    quarantine_review: RawInputQuarantineReviewV110,
    cross_review: PortfolioQuarantineCrossReviewV111,
) -> str:
    lines = [
        "# Portfolio / Raw Input Quarantine Cross-Review",
        "",
        "## Cross-Review Summary",
        f"- state: {cross_review.cross_review_state.value}",
        f"- portfolio quality: {portfolio_review.overall_severity}",
        f"- quarantine: {quarantine_review.quarantine_state.value}",
        f"- source: {cross_review.source_classification}",
        f"- Import Readiness: {cross_review.import_readiness}",
        f"- Cache Write Readiness: {cross_review.cache_write_readiness}",
        "",
        "## Common Validation Taxonomy Mapping",
    ]
    lines.extend(f"- {key}" for key in cross_review.shared_validation_keys)
    lines.extend(["", "## Manual Confirmations Required"])
    lines.extend(f"- {item}" for item in cross_review.manual_confirmation_items_ja or ("none",))
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in cross_review.next_actions_ja)
    lines.extend(
        [
            "",
            "## Safety Summary",
            f"- {cross_review.safety_note_ja}",
            "- broker API / raw Excel direct parsing: not executed / not approved",
            "- actual import / cache write: not executed / not approved",
            "- trading action / real email send: not executed / not approved",
            "",
        ]
    )
    return "\n".join(lines)


def format_portfolio_quarantine_cross_review_json_v111(
    portfolio_review: PortfolioDataQualityReviewV109,
    quarantine_review: RawInputQuarantineReviewV110,
    cross_review: PortfolioQuarantineCrossReviewV111,
) -> str:
    payload = {
        "portfolio_quality": asdict(portfolio_review),
        "quarantine": asdict(quarantine_review),
        "cross_review": asdict(cross_review),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=lambda value: value.value)
