"""Report UX language contract for user-facing decision-support outputs."""

from __future__ import annotations

from dataclasses import dataclass
import json


@dataclass(frozen=True)
class ReportUxLanguageRule:
    key: str
    label_ja: str
    required_wording_ja: str
    rationale_ja: str


@dataclass(frozen=True)
class ReportUxLanguageContract:
    schema_version: str
    source_mode: str
    rules: tuple[ReportUxLanguageRule, ...]
    forbidden_wording: tuple[str, ...]
    safety_notes: tuple[str, ...]


def build_report_ux_language_contract() -> ReportUxLanguageContract:
    return ReportUxLanguageContract(
        schema_version="report_ux_language_contract.v1",
        source_mode="source_only_language_contract",
        rules=(
            ReportUxLanguageRule(
                key="not_trade_instruction",
                label_ja="売買指示ではない",
                required_wording_ja="これは売買指示ではなく、確認・記録・リスク管理のための分類です。",
                rationale_ja="候補、月次スタンス、整理スコアを注文・売買推奨と誤読させない。",
            ),
            ReportUxLanguageRule(
                key="high_priority_review_meaning",
                label_ja="高優先レビューの意味",
                required_wording_ja="高優先レビューは深掘り順序であり、実行指示ではありません。",
                rationale_ja="HIGH_CONVICTION_REVIEWや高優先という語を買い煽りに見せない。",
            ),
            ReportUxLanguageRule(
                key="severity_meaning",
                label_ja="ERROR/WARN/INFOの意味",
                required_wording_ja="ERRORは契約不一致、WARNは人間確認、INFOは補足情報です。",
                rationale_ja="検証結果の重大度と投資判断の優先度を混同させない。",
            ),
            ReportUxLanguageRule(
                key="email_preview_not_delivery",
                label_ja="email previewと実送信の違い",
                required_wording_ja="email preview artifactは確認用であり、Gmail実送信ではありません。",
                rationale_ja="Gmail未着を障害と誤認せず、preview artifactを正本として確認する。",
            ),
            ReportUxLanguageRule(
                key="hard_gate_no_go",
                label_ja="NO-GO境界",
                required_wording_ja="actual import / broker API / raw Excel direct parsing / cache write はNO-GOです。",
                rationale_ja="未承認のデータ取込・売買・永続化に進まない。",
            ),
        ),
        forbidden_wording=(
            "買うべき",
            "売るべき",
            "必ず購入",
            "必ず売却",
            "今すぐ発注",
            "注文してください",
            "Gmail送信済み",
            "actual import approved",
            "cache write approved",
        ),
        safety_notes=(
            "This is a language contract only; it does not change scoring, veto, portfolio, or report generation semantics.",
            "No workflow change, workflow_dispatch, live HTTP, cache write, actual import, broker API, raw Excel parsing, secret display, trading action, or real email send is executed.",
        ),
    )


def validate_report_ux_language_text(
    text: str,
    contract: ReportUxLanguageContract | None = None,
) -> tuple[str, ...]:
    source = contract or build_report_ux_language_contract()
    issues: list[str] = []
    for forbidden in source.forbidden_wording:
        if forbidden in text:
            issues.append(f"forbidden_wording:{forbidden}")
    return tuple(issues)


def format_report_ux_language_contract_json(contract: ReportUxLanguageContract) -> str:
    payload = {
        "schema_version": contract.schema_version,
        "source_mode": contract.source_mode,
        "rules": [rule.__dict__ for rule in contract.rules],
        "forbidden_wording": list(contract.forbidden_wording),
        "safety_notes": list(contract.safety_notes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_report_ux_language_contract_markdown(contract: ReportUxLanguageContract) -> str:
    lines = [
        "# Report UX Language Contract",
        "",
        f"- schema_version: {contract.schema_version}",
        f"- source_mode: {contract.source_mode}",
        "",
        "## Required Clarifications",
        "",
        "| key | label | required wording | rationale |",
        "| --- | --- | --- | --- |",
    ]
    for rule in contract.rules:
        lines.append(
            f"| {rule.key} | {rule.label_ja} | {rule.required_wording_ja} | {rule.rationale_ja} |"
        )
    lines.extend(["", "## Forbidden Wording"])
    lines.extend(f"- {word}" for word in contract.forbidden_wording)
    lines.extend(["", "## Safety Notes"])
    lines.extend(f"- {note}" for note in contract.safety_notes)
    lines.append("")
    return "\n".join(lines)
