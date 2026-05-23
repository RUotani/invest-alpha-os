"""R7.0-Ops-J: post-run integrator tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.operator.post_run_integrate import (
    audit_pr,
    choose_integration_strategy,
    classify_pr_risk,
    detect_stacked_pr_chain,
    format_integrate_markdown,
    parse_pr_range,
    pr_numbers_from_evidence,
    run_post_run_integrate,
)


def _gh_json_response(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(payload), stderr="")


def _pr_payload(number: int, *, files: list[str], merge_state: str = "CLEAN") -> dict:
    return {
        "number": number,
        "title": f"PR {number}",
        "state": "OPEN",
        "isDraft": False,
        "mergeStateStatus": merge_state,
        "headRefName": f"branch-{number}",
        "files": [{"path": p} for p in files],
        "statusCheckRollup": [
            {
                "__typename": "CheckRun",
                "conclusion": "SUCCESS",
                "name": "test",
            }
        ],
    }


def test_parse_pr_range_hyphen_and_list() -> None:
    assert parse_pr_range("185-187") == [185, 186, 187]
    assert parse_pr_range("190,192") == [190, 192]


def test_classify_pr_risk_blocks_product_code() -> None:
    assert classify_pr_risk(["src/invis_alpha_os/foo.py"]) == "product_code"
    assert classify_pr_risk(["docs/a.md"]) == "docs_only"


def test_detect_stacked_pr_chain_true() -> None:
    from invis_alpha_os.operator.post_run_integrate import PrAuditRecord

    rows = [
        PrAuditRecord(1, "a", "OPEN", False, "CLEAN", True, ["docs/a.md"], "docs_only", True),
        PrAuditRecord(2, "b", "OPEN", False, "CLEAN", True, ["docs/a.md", "docs/b.md"], "docs_only", True),
        PrAuditRecord(
            3,
            "c",
            "OPEN",
            False,
            "CLEAN",
            True,
            ["docs/a.md", "docs/b.md", "tests/t.py"],
            "mixed_low_risk",
            True,
        ),
    ]
    assert detect_stacked_pr_chain(rows) is True
    assert choose_integration_strategy(rows) == "consolidation"


def test_pr_numbers_from_evidence() -> None:
    nums = pr_numbers_from_evidence(
        {
            "task_results": [
                {"pr_url": "https://github.com/org/repo/pull/185"},
                {"pr_url": "https://github.com/org/repo/pull/199"},
            ]
        }
    )
    assert nums == [185, 199]


def test_run_post_run_integrate_dry_run(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = "20260523T112747Z"
    ev_dir = tmp_path / "operator" / "dev_loop" / run_id
    ev_dir.mkdir(parents=True)
    (ev_dir / "evidence_summary.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "stop_reason": "early_completion: pr_cap_reached",
                "task_results": [
                    {"pr_url": "https://github.com/x/pull/185"},
                    {"pr_url": "https://github.com/x/pull/186"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "operator" / "productive_true_longrun_12h_v3" / run_id).mkdir(parents=True)

    def fake_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        num = int(cmd[3])
        files = ["docs/a.md"] if num == 185 else ["docs/a.md", "docs/b.md"]
        return _gh_json_response(_pr_payload(num, files=files))

    result = run_post_run_integrate(
        run_id=run_id,
        outputs_root=tmp_path,
        dry_run=True,
        integrate=False,
        gh_runner=fake_gh,
    )
    assert result.strategy == "consolidation"
    assert result.stacked_detected is True
    text = format_integrate_markdown(result)
    assert "consolidation" in text
    assert "185" in text


def test_integrate_requires_gate(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = "20260523T000001Z"
    ev_dir = tmp_path / "operator" / "dev_loop" / run_id
    ev_dir.mkdir(parents=True)
    (ev_dir / "evidence_summary.json").write_text(
        json.dumps({"task_results": [{"pr_url": "https://github.com/x/pull/1"}]}),
        encoding="utf-8",
    )
    (tmp_path / "operator" / "productive_true_longrun_8h" / run_id).mkdir(parents=True)

    def fake_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return _gh_json_response(_pr_payload(1, files=["docs/x.md"]))

    monkeypatch.delenv("CONFIRM_PRODUCTIVE_PR_MERGE", raising=False)
    result = run_post_run_integrate(
        run_id=run_id,
        pr_range="1",
        outputs_root=tmp_path,
        dry_run=False,
        integrate=True,
        gh_runner=fake_gh,
    )
    assert not result.gate_ok
    assert result.errors
