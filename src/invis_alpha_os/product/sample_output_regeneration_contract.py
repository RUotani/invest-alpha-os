"""Sample output regeneration contract (stdout-only / source-only)."""

from __future__ import annotations

from dataclasses import dataclass
import json


@dataclass(frozen=True)
class SampleOutputRegenerationCommand:
    id: str
    command: str
    output_mode: str
    expected_markers: tuple[str, ...]


@dataclass(frozen=True)
class SampleOutputRegenerationContract:
    schema_version: str
    source_mode: str
    commands: tuple[SampleOutputRegenerationCommand, ...]
    forbidden_actions: tuple[str, ...]
    operator_notes: tuple[str, ...]


def build_sample_output_regeneration_contract() -> SampleOutputRegenerationContract:
    return SampleOutputRegenerationContract(
        schema_version="sample_output_regeneration_contract.v1",
        source_mode="source_only_stdout_contract",
        commands=(
            SampleOutputRegenerationCommand(
                id="sample_output_pack_markdown",
                command="env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main sample-output-pack --format markdown",
                output_mode="stdout_only",
                expected_markers=(
                    "Sample Output Pack",
                    "Portfolio Data Quality Review",
                    "Raw Input Quarantine Review",
                    "Portfolio / Raw Input Quarantine Cross-Review",
                ),
            ),
            SampleOutputRegenerationCommand(
                id="operator_dashboard_summary_markdown",
                command="env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main operator-dashboard-summary --format markdown",
                output_mode="stdout_only",
                expected_markers=("Operator Dashboard Summary", "Primary Queue", "Hard Gate Status"),
            ),
            SampleOutputRegenerationCommand(
                id="progress_dashboard_check_markdown",
                command="env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main progress-dashboard-check --format markdown",
                output_mode="stdout_only_read_only",
                expected_markers=("Progress Dashboard Consistency Check", "ok: true", "Actual Import Readiness"),
            ),
            SampleOutputRegenerationCommand(
                id="state_consistency_check_markdown",
                command="env PYTHONPATH=src .venv/bin/python -m invis_alpha_os.cli.main state-consistency-check --format markdown",
                output_mode="stdout_only_read_only",
                expected_markers=("STATE.md Consistency Check", "read-only STATE.md consistency check", "workflow_dispatch"),
            ),
        ),
        forbidden_actions=(
            "workflow change",
            "manual workflow_dispatch",
            "live HTTP / market-data live fetch",
            "cache write",
            "actual import / manual import",
            "broker API / raw Excel direct parsing",
            "env/secret display",
            "trading action / order placement",
            "real email send",
        ),
        operator_notes=(
            "This contract lists allowed regeneration commands; it does not execute them.",
            "Commands are stdout-only or read-only unless a future explicit approval changes the boundary.",
            "Generated reports under reports/ and outputs/operator remain non-commit artifacts by policy.",
        ),
    )


def format_sample_output_regeneration_contract_json(contract: SampleOutputRegenerationContract) -> str:
    payload = {
        "schema_version": contract.schema_version,
        "source_mode": contract.source_mode,
        "commands": [command.__dict__ for command in contract.commands],
        "forbidden_actions": list(contract.forbidden_actions),
        "operator_notes": list(contract.operator_notes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_sample_output_regeneration_contract_markdown(contract: SampleOutputRegenerationContract) -> str:
    lines = [
        "# Sample Output Regeneration Contract",
        "",
        f"- schema_version: {contract.schema_version}",
        f"- source_mode: {contract.source_mode}",
        "",
        "## Commands",
        "",
        "| id | output mode | command | expected markers |",
        "| --- | --- | --- | --- |",
    ]
    for command in contract.commands:
        lines.append(
            f"| {command.id} | {command.output_mode} | `{command.command}` | {', '.join(command.expected_markers)} |"
        )
    lines.extend(["", "## Forbidden Actions"])
    lines.extend(f"- {action}" for action in contract.forbidden_actions)
    lines.extend(["", "## Operator Notes"])
    lines.extend(f"- {note}" for note in contract.operator_notes)
    lines.append("")
    return "\n".join(lines)
