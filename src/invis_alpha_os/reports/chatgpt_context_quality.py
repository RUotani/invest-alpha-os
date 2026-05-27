"""Quality audit for ChatGPT context pack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_REQUIRED_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "report_date",
    "generated_at",
    "summary",
    "candidates",
    "research_queue",
)
_ALLOWED_ASCII_LABEL_PREFIXES: tuple[str, ...] = (
    "ticker",
    "path",
    "env",
    "json",
    "md",
    "api",
    "chatgpt",
    "us",
    "jp",
    "etf",
)
_MAX_RECOMMENDED_MARKDOWN_CHARS = 18000


@dataclass(frozen=True)
class ContextQualityAuditResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _is_blank_text_list(value: Any) -> bool:
    if not isinstance(value, list):
        return True
    items = [str(x).strip() for x in value if str(x).strip()]
    return len(items) == 0


def _count_excessive_ascii_labels(markdown_text: str) -> int:
    count = 0
    for raw in markdown_text.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        label = line.split(":", 1)[0].strip().lstrip("-# ").lower().replace(" ", "")
        if not label:
            continue
        if any(label.startswith(prefix) for prefix in _ALLOWED_ASCII_LABEL_PREFIXES):
            continue
        if all(ord(ch) < 128 for ch in label):
            count += 1
    return count


def build_context_pack_quality_audit(
    *,
    report_date: str,
    context_json_payload: dict[str, Any],
    context_markdown_text: str | None = None,
) -> ContextQualityAuditResult:
    missing_required = [k for k in _REQUIRED_TOP_LEVEL_KEYS if k not in context_json_payload]
    candidates = context_json_payload.get("candidates")
    candidate_rows = [x for x in candidates if isinstance(x, dict)] if isinstance(candidates, list) else []
    candidate_count = len(candidate_rows)

    stale_data_count = 0
    missing_quant_count = 0
    empty_momentum_count = 0
    empty_counter_evidence_count = 0
    empty_next_checks_count = 0
    empty_questions_count = 0
    source_missing_count = 0
    missing_fields: list[str] = []

    for row in candidate_rows:
        freshness = str(row.get("freshness", "")).lower()
        if "stale" in freshness:
            stale_data_count += 1
        if row.get("latest_close") is None:
            missing_quant_count += 1
        if _is_blank_text_list(row.get("momentum_rationale")):
            empty_momentum_count += 1
        if _is_blank_text_list(row.get("counter_evidence")):
            empty_counter_evidence_count += 1
        if _is_blank_text_list(row.get("next_checks")):
            empty_next_checks_count += 1
        if _is_blank_text_list(row.get("chatgpt_questions")):
            empty_questions_count += 1
        if _is_blank_text_list(row.get("sources")):
            source_missing_count += 1
        for key in ("ticker", "name", "classification"):
            if not str(row.get(key, "")).strip():
                missing_fields.append(f"{row.get('rank', '?')}:{key}")

    md_char_count = len(context_markdown_text or "")
    md_line_count = len((context_markdown_text or "").splitlines())
    ascii_label_count = _count_excessive_ascii_labels(context_markdown_text or "")

    if candidate_count == 0 or len(missing_required) >= 2:
        grade = "D"
    elif (
        empty_momentum_count > candidate_count // 2
        or empty_counter_evidence_count > candidate_count // 2
        or empty_next_checks_count > candidate_count // 2
    ):
        grade = "C"
    elif (
        missing_required
        or stale_data_count > 0
        or missing_quant_count > 0
        or empty_questions_count > 0
        or ascii_label_count > 0
    ):
        grade = "B"
    else:
        grade = "A"

    audit_payload: dict[str, Any] = {
        "report_date": report_date,
        "grade": grade,
        "candidate_count": candidate_count,
        "required_sections_missing": missing_required,
        "missing_fields": missing_fields[:50],
        "stale_data_count": stale_data_count,
        "missing_quant_count": missing_quant_count,
        "empty_momentum_count": empty_momentum_count,
        "empty_counter_evidence_count": empty_counter_evidence_count,
        "empty_next_checks_count": empty_next_checks_count,
        "empty_chatgpt_questions_count": empty_questions_count,
        "source_missing_count": source_missing_count,
        "japanese_label_check": {
            "excessive_ascii_label_count": ascii_label_count,
            "allowed_english_prefixes": list(_ALLOWED_ASCII_LABEL_PREFIXES),
        },
        "length_check": {
            "markdown_char_count": md_char_count,
            "markdown_line_count": md_line_count,
            "recommended_max_chars": _MAX_RECOMMENDED_MARKDOWN_CHARS,
            "is_too_long": md_char_count > _MAX_RECOMMENDED_MARKDOWN_CHARS,
        },
    }

    md_lines = [
        "# Context Pack 品質監査",
        "",
        f"- 対象日: {report_date}",
        f"- 総合グレード: {grade}",
        f"- 候補数: {candidate_count}",
        "",
        "## 監査サマリー",
        f"- 必須セクション欠落: {len(missing_required)}",
        f"- staleデータ件数: {stale_data_count}",
        f"- 定量不足件数: {missing_quant_count}",
        f"- モメンタム根拠空欄: {empty_momentum_count}",
        f"- 反証空欄: {empty_counter_evidence_count}",
        f"- 次確認空欄: {empty_next_checks_count}",
        f"- ChatGPT質問空欄: {empty_questions_count}",
        f"- 出典不足: {source_missing_count}",
        f"- 日本語ラベル警告数: {ascii_label_count}",
        f"- 長さ警告: {'あり' if md_char_count > _MAX_RECOMMENDED_MARKDOWN_CHARS else 'なし'}",
        "",
        "## 補足",
        f"- 欠落セクション: {', '.join(missing_required) or 'なし'}",
        f"- 欠落フィールド(先頭50件): {', '.join(missing_fields[:10]) or 'なし'}",
        "",
    ]
    return ContextQualityAuditResult(markdown_text="\n".join(md_lines), json_payload=audit_payload)
