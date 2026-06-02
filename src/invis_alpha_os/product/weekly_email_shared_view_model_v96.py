"""v96 Weekly/email shared view model (source-only / fixture-only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeeklySharedViewModelV96:
    safety_note_ja: str
    score_veto_summary_lines: tuple[str, ...]
    pipeline_summary_lines: tuple[str, ...]
    monthly_input_summary_lines: tuple[str, ...]


_DEFAULT_SAFETY_NOTE = "これは売買指示ではなく、根拠補完・安全確認・深掘り優先度の分類です。"


def build_weekly_shared_view_model_v96(
    *,
    score_veto_summary_lines: tuple[str, ...],
    pipeline_summary_lines: tuple[str, ...],
    monthly_input_summary_lines: tuple[str, ...],
    safety_note_ja: str = _DEFAULT_SAFETY_NOTE,
) -> WeeklySharedViewModelV96:
    return WeeklySharedViewModelV96(
        safety_note_ja=safety_note_ja,
        score_veto_summary_lines=score_veto_summary_lines,
        pipeline_summary_lines=pipeline_summary_lines,
        monthly_input_summary_lines=monthly_input_summary_lines,
    )


def render_weekly_shared_view_model_markdown_v96(model: WeeklySharedViewModelV96) -> list[str]:
    lines: list[str] = [
        "## Shared Summary（v96）",
        "",
        "### Score / Veto（共有要約）",
    ]
    if model.score_veto_summary_lines:
        lines.extend(f"- {x}" for x in model.score_veto_summary_lines)
    lines.extend(["", "### 候補パイプライン（共有要約）"])
    if model.pipeline_summary_lines:
        lines.extend(f"- {x}" for x in model.pipeline_summary_lines)
    lines.extend(["", "### Monthly Input Consistency（共有要約）"])
    if model.monthly_input_summary_lines:
        lines.extend(f"- {x}" for x in model.monthly_input_summary_lines)
    lines.extend(["", f"- {model.safety_note_ja}", ""])
    return lines


def render_weekly_shared_view_model_email_text_v96(model: WeeklySharedViewModelV96) -> tuple[str, ...]:
    lines: list[str] = []
    lines.extend(model.pipeline_summary_lines)
    lines.extend(model.score_veto_summary_lines)
    lines.extend(model.monthly_input_summary_lines)
    lines.append(model.safety_note_ja)
    return tuple(x for x in lines if x)


def extract_weekly_shared_view_model_from_copy_v96(copy_body: str) -> WeeklySharedViewModelV96:
    score: list[str] = []
    pipeline: list[str] = []
    monthly: list[str] = []
    safety = _DEFAULT_SAFETY_NOTE
    for raw in copy_body.splitlines():
        line = raw.strip()
        if line.startswith("- 候補パイプライン:"):
            pipeline.append(line.removeprefix("- ").strip())
        elif line.startswith("- 主因:"):
            pipeline.append(line.removeprefix("- ").strip())
        elif line.startswith("- Score/Veto:"):
            score.append(line.removeprefix("- ").strip())
        elif line == "- これは実行指示ではなく、根拠補完と安全確認の分類です。":
            score.append(line.removeprefix("- ").strip())
            safety = _DEFAULT_SAFETY_NOTE
        elif line.startswith("- Monthly Input:"):
            monthly.append(line.removeprefix("- ").strip())
        elif line.startswith("- Monthly Guardrail:"):
            monthly.append(line.removeprefix("- ").strip())
    return build_weekly_shared_view_model_v96(
        score_veto_summary_lines=tuple(score),
        pipeline_summary_lines=tuple(pipeline),
        monthly_input_summary_lines=tuple(monthly),
        safety_note_ja=safety,
    )
