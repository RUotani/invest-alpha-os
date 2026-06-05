"""v1.0 operational readiness summary for Candidate Discovery OS daily use."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from invis_alpha_os.product.progress_dashboard_consistency import check_progress_dashboard_consistency

_V1_SCHEMA = "v1_operational_readiness.v1"
_CORE_ITEM_COUNT = 12
_OBSERVATION_ITEM_COUNT = 2
_BOUNDARY_ITEM_COUNT = 1
_FIXED_TOTAL = _CORE_ITEM_COUNT + _OBSERVATION_ITEM_COUNT + _BOUNDARY_ITEM_COUNT


@dataclass(frozen=True)
class V1ReadinessItem:
    item_id: str
    category: str
    status: str
    summary: str
    verify_hint: str


@dataclass(frozen=True)
class V1OperationalReadinessResult:
    schema_version: str
    source_mode: str
    target_use_date: str
    latest_verified_main_note: str
    schedule_status: str
    delivery_mode: str
    gmail_sent: bool
    core_ready: int
    core_total: int
    observation_ready: int
    observation_total: int
    boundary_ready: int
    boundary_total: int
    v1_usable_tomorrow: bool
    progress_dashboard_ok: bool
    items: tuple[V1ReadinessItem, ...]
    recommended_next_actions: tuple[str, ...]


def _file_exists(repo_root: Path, relative: str) -> bool:
    return (repo_root / relative).is_file()


def build_v1_operational_readiness(
    *,
    repo_root: Path,
    target_use_date: str = "2026-06-07",
) -> V1OperationalReadinessResult:
    """Build a fixed-denominator v1.0 readiness view without side effects."""

    dashboard = check_progress_dashboard_consistency(repo_root / "docs" / "progress_dashboard.md")
    progress_ok = dashboard.ok

    core_items = (
        V1ReadinessItem(
            item_id="weekly_brief_zero_candidate",
            category="core",
            status="ready",
            summary="候補0件週の結論・guardrail・非売買指示（#487）。",
            verify_hint="pytest tests/test_weekly_report_user_readability_contract.py",
        ),
        V1ReadinessItem(
            item_id="weekly_brief_candidate_positive",
            category="core",
            status="ready",
            summary="候補あり週の短縮結論テンプレ（#495 D4）。",
            verify_hint="pytest tests/test_weekly_candidate_positive_conclusion_v113.py",
        ),
        V1ReadinessItem(
            item_id="weekly_report_user_summary_cli",
            category="core",
            status="ready",
            summary="one-page summary を fixture/composed から stdout 出力。",
            verify_hint="weekly-report-user-summary --format markdown --source composed",
        ),
        V1ReadinessItem(
            item_id="weekly_artifact_local_verify_cli",
            category="core",
            status="ready",
            summary="artifact/status.json を read-only 検証。",
            verify_hint="weekly-artifact-local-verify --report-date <date> --json-report-optional",
        ),
        V1ReadinessItem(
            item_id="operator_dashboard_summary_cli",
            category="core",
            status="ready",
            summary="operator 向けキュー・Hard Gate 要約。",
            verify_hint="operator-dashboard-summary --format markdown",
        ),
        V1ReadinessItem(
            item_id="progress_dashboard_consistency",
            category="core",
            status="ready" if progress_ok else "pending",
            summary="固定分母 progress dashboard の整合チェック。",
            verify_hint="progress-dashboard-check --format markdown",
        ),
        V1ReadinessItem(
            item_id="project_goal_doc",
            category="core",
            status="ready" if _file_exists(repo_root, "docs/project_goal_candidate_discovery_os.md") else "pending",
            summary="Global Multi-Asset Candidate Discovery OS 目的の明文化。",
            verify_hint="docs/project_goal_candidate_discovery_os.md",
        ),
        V1ReadinessItem(
            item_id="operator_user_guide",
            category="core",
            status="ready" if _file_exists(repo_root, "docs/operator_user_guide.md") else "pending",
            summary="週次観測・artifact 検証の安全コマンド索引。",
            verify_hint="docs/operator_user_guide.md",
        ),
        V1ReadinessItem(
            item_id="weekly_10min_flow_doc",
            category="core",
            status="ready" if _file_exists(repo_root, "docs/v1_0_weekly_10min_flow.md") else "pending",
            summary="週次10分レビューフロー（Candidate Brief 中心）。",
            verify_hint="docs/v1_0_weekly_10min_flow.md",
        ),
        V1ReadinessItem(
            item_id="tomorrow_checklist_doc",
            category="core",
            status="ready" if _file_exists(repo_root, "docs/v1_0_tomorrow_operational_checklist.md") else "pending",
            summary="初日運用チェックリスト（read-only / fixture-first）。",
            verify_hint="docs/v1_0_tomorrow_operational_checklist.md",
        ),
        V1ReadinessItem(
            item_id="one_page_summary_sample",
            category="core",
            status="ready"
            if _file_exists(repo_root, "reports-private/sample_outputs/chatgpt_one_page_summary_sample.md")
            else "pending",
            summary="ChatGPT 貼付用 one-page サンプル。",
            verify_hint="reports-private/sample_outputs/chatgpt_one_page_summary_sample.md",
        ),
        V1ReadinessItem(
            item_id="monthly_decision_sheet_fixture",
            category="core",
            status="ready"
            if _file_exists(repo_root, "reports-private/sample_outputs/monthly_decision_sheet_sample.md")
            else "pending",
            summary="月次 Decision Sheet fixture sample。",
            verify_hint="monthly-review-pack-integration --format markdown",
        ),
    )

    observation_items = (
        V1ReadinessItem(
            item_id="scheduled_natural_run",
            category="observation",
            status="pending",
            summary="2026-06-06 07:30 JST 以降 event=schedule の read-only 観測。",
            verify_hint="gh run list --workflow weekly_candidate_brief.yml",
        ),
        V1ReadinessItem(
            item_id="ci_json_artifact_upload",
            category="observation",
            status="pending",
            summary="workflow JSON upload path は承認待ち（proposal のみ）。",
            verify_hint="docs/proposals/2026-06-06_weekly_workflow_artifact_patch_proposal.md",
        ),
    )

    boundary_items = (
        V1ReadinessItem(
            item_id="actual_import_auto_trading",
            category="boundary",
            status="ready",
            summary="actual import / broker / 自動売買は意図的 NO-GO（v1.0 対象外）。",
            verify_hint="docs/project_goal_candidate_discovery_os.md",
        ),
    )

    items = core_items + observation_items + boundary_items
    core_ready = sum(1 for item in core_items if item.status == "ready")
    observation_ready = sum(1 for item in observation_items if item.status == "ready")
    boundary_ready = sum(1 for item in boundary_items if item.status == "ready")
    v1_usable = core_ready == _CORE_ITEM_COUNT

    return V1OperationalReadinessResult(
        schema_version=_V1_SCHEMA,
        source_mode="source_only_read_only_no_side_effects",
        target_use_date=target_use_date,
        latest_verified_main_note="Post #497 — Candidate Discovery OS v1.0 operational pack",
        schedule_status="pending",
        delivery_mode="local_markdown_or_artifact_preview",
        gmail_sent=False,
        core_ready=core_ready,
        core_total=_CORE_ITEM_COUNT,
        observation_ready=observation_ready,
        observation_total=_OBSERVATION_ITEM_COUNT,
        boundary_ready=boundary_ready,
        boundary_total=_BOUNDARY_ITEM_COUNT,
        v1_usable_tomorrow=v1_usable,
        progress_dashboard_ok=progress_ok,
        items=items,
        recommended_next_actions=(
            "毎朝: v1-readiness-check --format markdown で core 12/12 を確認。",
            "週次: docs/v1_0_weekly_10min_flow.md に従い Candidate Brief をレビュー。",
            "2026-06-06 07:30 JST 以降: scheduled run を read-only 観測し artifact verify。",
            "workflow JSON upload は人間承認まで proposal のみ維持。",
        ),
    )


def format_v1_operational_readiness_json(result: V1OperationalReadinessResult) -> str:
    payload = {
        "schema_version": result.schema_version,
        "source_mode": result.source_mode,
        "target_use_date": result.target_use_date,
        "latest_verified_main_note": result.latest_verified_main_note,
        "schedule_status": result.schedule_status,
        "delivery_mode": result.delivery_mode,
        "gmail_sent": result.gmail_sent,
        "core_ready": result.core_ready,
        "core_total": result.core_total,
        "observation_ready": result.observation_ready,
        "observation_total": result.observation_total,
        "boundary_ready": result.boundary_ready,
        "boundary_total": result.boundary_total,
        "fixed_total": _FIXED_TOTAL,
        "v1_usable_tomorrow": result.v1_usable_tomorrow,
        "progress_dashboard_ok": result.progress_dashboard_ok,
        "items": [item.__dict__ for item in result.items],
        "recommended_next_actions": list(result.recommended_next_actions),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_v1_operational_readiness_markdown(result: V1OperationalReadinessResult) -> str:
    core_pct = round((result.core_ready / result.core_total) * 100) if result.core_total else 0
    lines = [
        "# v1.0 Operational Readiness — Candidate Discovery OS",
        "",
        f"- schema_version: {result.schema_version}",
        f"- source_mode: {result.source_mode}",
        f"- target_use_date: {result.target_use_date}",
        f"- latest_verified_main_note: {result.latest_verified_main_note}",
        f"- schedule_status: **{result.schedule_status}**",
        f"- delivery_mode: **{result.delivery_mode}**",
        f"- gmail_sent: **{str(result.gmail_sent).lower()}**",
        f"- v1_usable_tomorrow: **{str(result.v1_usable_tomorrow).lower()}**",
        f"- core: **{result.core_ready}/{result.core_total} ({core_pct}%)**",
        f"- observation: {result.observation_ready}/{result.observation_total}",
        f"- boundary (intentional NO-GO): {result.boundary_ready}/{result.boundary_total}",
        f"- progress_dashboard_ok: {str(result.progress_dashboard_ok).lower()}",
        "",
        "## Core（明日からの実用）",
        "",
        "| id | status | summary | verify |",
        "| --- | --- | --- | --- |",
    ]
    for item in result.items:
        if item.category != "core":
            continue
        lines.append(f"| {item.item_id} | {item.status} | {item.summary} | `{item.verify_hint}` |")
    lines.extend(
        [
            "",
            "## Observation（v1.0 完全化待ち）",
            "",
            "| id | status | summary | verify |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in result.items:
        if item.category != "observation":
            continue
        lines.append(f"| {item.item_id} | {item.status} | {item.summary} | `{item.verify_hint}` |")
    lines.extend(
        [
            "",
            "## Boundary（意図的 NO-GO）",
            "",
            "| id | status | summary |",
            "| --- | --- | --- |",
        ]
    )
    for item in result.items:
        if item.category != "boundary":
            continue
        lines.append(f"| {item.item_id} | {item.status} | {item.summary} |")
    lines.extend(["", "## Recommended Next Actions"])
    lines.extend(f"- {action}" for action in result.recommended_next_actions)
    lines.extend(
        [
            "",
            "## Safety Notes",
            "- Gmail inbox is not the canonical v1.0 delivery mechanism",
            "- canonical outputs are local Markdown reports and email preview artifacts",
            "- not an auto-trading bot; no broker API; no order placement",
            "- workflow_dispatch / workflow change / live HTTP / cache write / actual import: not executed",
            "- real email send / trading action / env secret display: not executed",
            "",
        ]
    )
    return "\n".join(lines)
