"""Long-run completion detection and best-effort operator notifications."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable


def detect_early_completion(
    *,
    status: str,
    stop_reason: str,
    safety_validator_status: str,
    tasks_seen: int,
    tasks_executed: int,
    prs_created: int,
    task_results_count: int,
    skipped_task_count: int,
    cap_reached_tasks: bool,
    cap_reached_prs: bool,
    failed_task_count: int,
    max_task_failures: int | None,
    continue_on_task_failure: bool,
    is_real_failure: bool,
) -> tuple[bool, str]:
    """Return whether productive queue work is done and heartbeat-only wait has no new value."""
    if is_real_failure or status == "blocked" or safety_validator_status == "failed":
        return False, ""
    if continue_on_task_failure and max_task_failures is not None:
        if failed_task_count > max_task_failures:
            return False, ""
    elif failed_task_count > 0 and status == "stopped":
        return False, ""

    reasons: list[str] = []
    if cap_reached_tasks:
        reasons.append("task_cap_reached")
    if cap_reached_prs:
        reasons.append("pr_cap_reached")
    handled = task_results_count + skipped_task_count
    if tasks_seen > 0 and handled >= tasks_seen:
        reasons.append("queue_exhausted")
    if not reasons:
        return False, ""
    return True, ",".join(reasons)


def build_early_completion_meta(
    *,
    reason: str,
    tasks_executed: int,
    prs_created: int,
    remaining_runtime_minutes: float,
) -> dict[str, Any]:
    return {
        "early_completion_detected": True,
        "early_completion_reason": reason,
        "tasks_executed": tasks_executed,
        "prs_created": prs_created,
        "remaining_runtime_minutes": round(remaining_runtime_minutes, 2),
        "operator_action_required": (
            "review open PRs, run post-run-review, merge manually (no auto-merge)"
        ),
    }


def completion_event_from_result(
    *,
    status: str,
    stop_reason: str,
    longrun_state: str,
    longrun_exit_success: bool,
    is_real_failure: bool,
    dev_loop_rc: int = 0,
) -> str:
    if is_real_failure or status == "blocked":
        return "failure"
    if dev_loop_rc in {130, 143}:
        return "interrupted"
    if longrun_state == "early_completion":
        return "early_completion"
    if longrun_exit_success or stop_reason.startswith("min_runtime reached:"):
        return "min_runtime_reached"
    if status in {"completed", "completed_with_failures"}:
        return "completed"
    return "failure"


def emit_completion_notification(
    *,
    event: str,
    title: str,
    message: str,
    enable_sound: bool = True,
    enable_osascript: bool = True,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Best-effort macOS notification; never raises."""
    runner = subprocess_run or subprocess.run
    status: dict[str, Any] = {
        "event": event,
        "sound": "skipped",
        "osascript": "skipped",
    }
    if enable_sound:
        for sound_path in (
            "/System/Library/Sounds/Ping.aiff",
            "/System/Library/Sounds/Glass.aiff",
        ):
            if Path(sound_path).is_file():
                proc = runner(
                    ["afplay", sound_path],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                status["sound"] = "ok" if proc.returncode == 0 else f"failed:{proc.returncode}"
                break
        else:
            status["sound"] = "missing"
    if enable_osascript:
        safe_msg = message.replace('"', "'")[:200]
        safe_title = title.replace('"', "'")[:60]
        script = f'display notification {shlex.quote(safe_msg)} with title {shlex.quote(safe_title)}'
        proc = runner(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        status["osascript"] = "ok" if proc.returncode == 0 else f"failed:{proc.returncode}"
    return status
