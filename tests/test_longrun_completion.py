"""Unit tests for long-run early completion and completion notification."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from invis_alpha_os.operator.longrun_completion import (
    build_early_completion_meta,
    completion_event_from_result,
    detect_early_completion,
    emit_completion_notification,
)


def test_detect_early_completion_queue_exhausted() -> None:
    early, reason = detect_early_completion(
        status="completed",
        stop_reason="",
        safety_validator_status="ok",
        tasks_seen=8,
        tasks_executed=8,
        prs_created=8,
        task_results_count=8,
        skipped_task_count=0,
        cap_reached_tasks=False,
        cap_reached_prs=False,
        failed_task_count=0,
        max_task_failures=8,
        continue_on_task_failure=True,
        is_real_failure=False,
    )
    assert early is True
    assert "queue_exhausted" in reason


def test_detect_early_completion_blocked_on_failure() -> None:
    early, _ = detect_early_completion(
        status="stopped",
        stop_reason="max_runtime reached: 750m",
        safety_validator_status="ok",
        tasks_seen=8,
        tasks_executed=8,
        prs_created=8,
        task_results_count=8,
        skipped_task_count=0,
        cap_reached_tasks=False,
        cap_reached_prs=False,
        failed_task_count=0,
        max_task_failures=None,
        continue_on_task_failure=False,
        is_real_failure=True,
    )
    assert early is False


def test_build_early_completion_meta_fields() -> None:
    meta = build_early_completion_meta(
        reason="queue_exhausted",
        tasks_executed=8,
        prs_created=8,
        remaining_runtime_minutes=471.5,
    )
    assert meta["early_completion_detected"] is True
    assert meta["early_completion_reason"] == "queue_exhausted"
    assert meta["tasks_executed"] == 8
    assert meta["prs_created"] == 8
    assert meta["remaining_runtime_minutes"] == 471.5
    assert "operator_action_required" in meta


def test_completion_event_from_result_failure_and_interrupted() -> None:
    assert (
        completion_event_from_result(
            status="blocked",
            stop_reason="missing gate",
            longrun_state="",
            longrun_exit_success=False,
            is_real_failure=True,
        )
        == "failure"
    )
    assert (
        completion_event_from_result(
            status="stopped",
            stop_reason="",
            longrun_state="heartbeat_waiting",
            longrun_exit_success=False,
            is_real_failure=False,
            dev_loop_rc=130,
        )
        == "interrupted"
    )


def test_completion_event_from_result_early() -> None:
    assert (
        completion_event_from_result(
            status="completed",
            stop_reason="early_completion: queue_exhausted",
            longrun_state="early_completion",
            longrun_exit_success=True,
            is_real_failure=False,
        )
        == "early_completion"
    )


def test_emit_completion_notification_uses_subprocess_mock() -> None:
    proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    runner = MagicMock(return_value=proc)
    status = emit_completion_notification(
        event="completed",
        title="dev-loop completed",
        message="run ok",
        enable_sound=True,
        enable_osascript=True,
        subprocess_run=runner,
    )
    assert status["event"] == "completed"
    assert runner.call_count >= 1
