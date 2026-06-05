from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.v1_operational_readiness import (
    build_v1_operational_readiness,
    format_v1_operational_readiness_json,
    render_v1_operational_readiness_markdown,
)

REPO = Path(__file__).resolve().parents[1]


def test_v1_readiness_current_repo_core_items_ready() -> None:
    result = build_v1_operational_readiness(repo_root=REPO)

    assert result.core_total == 12
    assert result.v1_usable_tomorrow is True
    assert result.core_ready == 12
    assert result.boundary_ready == 1
    assert result.observation_ready == 0
    by_id = {item.item_id: item for item in result.items}
    assert by_id["weekly_brief_candidate_positive"].status == "ready"
    assert by_id["scheduled_natural_run"].status == "pending"


def test_v1_readiness_fails_when_required_doc_missing(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "progress_dashboard.md").write_text(
        (REPO / "docs" / "progress_dashboard.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = build_v1_operational_readiness(repo_root=tmp_path)

    assert result.v1_usable_tomorrow is False
    assert result.core_ready < result.core_total


def test_v1_readiness_markdown_and_json_renderers() -> None:
    result = build_v1_operational_readiness(repo_root=REPO)
    markdown = render_v1_operational_readiness_markdown(result)
    payload = json.loads(format_v1_operational_readiness_json(result))

    assert markdown.startswith("# v1.0 Operational Readiness")
    assert "v1_usable_tomorrow: **true**" in markdown
    assert "scheduled_natural_run" in markdown
    assert payload["schema_version"] == "v1_operational_readiness.v1"
    assert payload["v1_usable_tomorrow"] is True


def test_v1_readiness_check_cli_passes_on_current_repo() -> None:
    result = CliRunner().invoke(
        app,
        ["v1-readiness-check", "--repo-root", str(REPO), "--format", "markdown"],
    )

    assert result.exit_code == 0
    assert "v1_usable_tomorrow: **true**" in result.stdout


def test_v1_readiness_check_cli_nonzero_when_core_incomplete(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "progress_dashboard.md").write_text(
        (REPO / "docs" / "progress_dashboard.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["v1-readiness-check", "--repo-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["v1_usable_tomorrow"] is False
