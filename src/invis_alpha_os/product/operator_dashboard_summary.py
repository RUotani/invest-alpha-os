"""Source-only operator dashboard summary for the main development queue."""

from __future__ import annotations

from dataclasses import dataclass
import json


@dataclass(frozen=True)
class OperatorDashboardItem:
    key: str
    status: str
    summary: str
    next_check: str


@dataclass(frozen=True)
class OperatorDashboardSummary:
    schema_version: str
    source_mode: str
    latest_verified_main_note: str
    queue_items: tuple[OperatorDashboardItem, ...]
    hard_gate_status: tuple[OperatorDashboardItem, ...]
    recommended_next_actions: tuple[str, ...]


def build_operator_dashboard_summary() -> OperatorDashboardSummary:
    return OperatorDashboardSummary(
        schema_version="operator_dashboard_summary.v1",
        source_mode="source_only_stdout_no_side_effects",
        latest_verified_main_note="post #477 main includes P1/P2 local verification and P3 golden snapshots",
        queue_items=(
            OperatorDashboardItem(
                key="P1_scheduled_natural_run_observation",
                status="pending_not_yet_observable",
                summary="2026-06-06 07:30 JST以降にschedule eventをread-onlyで確認する。",
                next_check="gh run listでevent=scheduleの有無を先に分類する。",
            ),
            OperatorDashboardItem(
                key="P2_weekly_artifact_status_local_verification",
                status="ready",
                summary="CLI weekly-artifact-local-verifyでartifact/status.jsonを検証できる。",
                next_check="scheduled artifact bundleまたはlocal runner出力に対して実行する。",
            ),
            OperatorDashboardItem(
                key="P3_weekly_monthly_golden_snapshots",
                status="ready",
                summary="週次/月次の重要見出し、数値、安全文言、JSON契約をfixture-onlyで固定済み。",
                next_check="UX変更時は同じPRでsnapshot期待値と理由を更新する。",
            ),
            OperatorDashboardItem(
                key="P4_operator_dashboard_cli_summary",
                status="ready",
                summary="このCLIでoperator向け要約をstdoutに出せる。",
                next_check="Secondary queueのprogress/STATE consistency checkerへ接続する。",
            ),
        ),
        hard_gate_status=(
            OperatorDashboardItem(
                key="provider_live_http",
                status="not_executed_not_approved",
                summary="provider/market-data live HTTPは未実行・未承認。",
                next_check="承認packなしに実行しない。",
            ),
            OperatorDashboardItem(
                key="cache_write_actual_import",
                status="not_executed_not_approved",
                summary="cache write / actual import / manual importは未実行・未承認。",
                next_check="Actual Import Readinessは0%のまま扱う。",
            ),
            OperatorDashboardItem(
                key="broker_raw_input_secret_email_trading",
                status="not_executed_not_approved",
                summary="broker API、raw Excel parsing、env/secret表示、実メール送信、trading actionは未実行。",
                next_check="source-only / fixture-only境界を維持する。",
            ),
            OperatorDashboardItem(
                key="workflow_change_dispatch",
                status="not_executed_not_approved",
                summary="workflow変更とmanual workflow_dispatchは未実行・未承認。",
                next_check="P1は自然runのread-only観測のみで進める。",
            ),
        ),
        recommended_next_actions=(
            "2026-06-06 07:30 JST以降、scheduled natural runをread-onlyで観測する。",
            "artifactが存在する場合はweekly-artifact-local-verifyでstatus.jsonと本文マーカーを検査する。",
            "Secondary queueではprogress dashboardとSTATE.mdの整合性をsource-only checker化する。",
        ),
    )


def format_operator_dashboard_summary_json(summary: OperatorDashboardSummary) -> str:
    payload = {
        "schema_version": summary.schema_version,
        "source_mode": summary.source_mode,
        "latest_verified_main_note": summary.latest_verified_main_note,
        "queue_items": [item.__dict__ for item in summary.queue_items],
        "hard_gate_status": [item.__dict__ for item in summary.hard_gate_status],
        "recommended_next_actions": list(summary.recommended_next_actions),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_operator_dashboard_summary_markdown(summary: OperatorDashboardSummary) -> str:
    lines = [
        "# Operator Dashboard Summary",
        "",
        f"- schema_version: {summary.schema_version}",
        f"- source_mode: {summary.source_mode}",
        f"- latest_verified_main_note: {summary.latest_verified_main_note}",
        "",
        "## Primary Queue",
        "",
        "| key | status | summary | next check |",
        "| --- | --- | --- | --- |",
    ]
    for item in summary.queue_items:
        lines.append(f"| {item.key} | {item.status} | {item.summary} | {item.next_check} |")
    lines.extend(
        [
            "",
            "## Hard Gate Status",
            "",
            "| key | status | summary | next check |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in summary.hard_gate_status:
        lines.append(f"| {item.key} | {item.status} | {item.summary} | {item.next_check} |")
    lines.extend(["", "## Recommended Next Actions"])
    lines.extend(f"- {action}" for action in summary.recommended_next_actions)
    lines.append("")
    return "\n".join(lines)
