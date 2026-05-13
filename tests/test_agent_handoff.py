"""Main R0.5 agent handoff: strict summary writer + no live-ingest shortcuts in checker script."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_PY = _ROOT / "scripts" / "agent_handoff_summary.py"
_SHELL = _ROOT / "scripts" / "agent_final_check.sh"
_MAKEFILE = _ROOT / "Makefile"


def _load_handoff_module():
    spec = importlib.util.spec_from_file_location("agent_handoff_summary_test", _SCRIPT_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_agent_scripts_exist_and_makefile_targets() -> None:
    assert _SCRIPT_PY.is_file()
    assert _SHELL.is_file()
    makefile = _MAKEFILE.read_text(encoding="utf-8")
    assert "agent-final-check:" in makefile
    assert "scripts/agent_final_check.sh" in makefile


def test_ops_directory_gitignored_for_handoff_writes() -> None:
    ig = (_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(line.strip().rstrip("/") == "outputs/ops" or line.startswith("outputs/ops/") for line in ig)


def test_agent_final_check_shell_does_not_read_dotenv_via_daily_check_wrapper() -> None:
    txt = _SHELL.read_text(encoding="utf-8")
    assert "load_jquants_env.py" not in txt
    assert "--env-file" not in txt


def test_agent_final_check_shell_no_known_live_hooks() -> None:
    txt = _SHELL.read_text(encoding="utf-8")
    for tok in ("jquants-smoke-live", "jq-cache-live", "jq-cache-live-codes", "CONFIRM_LIVE_HTTP", "urllib.request"):
        assert tok not in txt


def test_agent_daily_momentum_no_env_script_boundary() -> None:
    path = _ROOT / "scripts" / "agent_daily_momentum_check_no_env.sh"
    assert path.is_file()
    txt2 = path.read_text(encoding="utf-8")
    assert "load_jquants_env.py" not in txt2
    assert "--env-file" not in txt2


@pytest.mark.parametrize("path", [_SHELL], ids=["agent_final_check.sh"])
def test_agent_final_check_bash_syntax(path: Path) -> None:
    subprocess.run(["bash", "-n", str(path)], check=True)


def test_validate_handoff_rejects_live_http_truthy() -> None:
    mod = _load_handoff_module()
    payload = {
        "pytest_exit_code": 0,
        "pytest_stdout_tail": "12 passed in 1s",
        "signals_exit_code": 0,
        "signals_json": None,
        "daily_momentum_exit_code": 0,
        "investment_os_coverage_exit_code": 0,
        "investment_stdout_tail": "",
        "post_push_stdout_tail": "",
        "post_push_classification": "skipped_no_gh",
        "git_status_lines": "",
        "live_http_performed": True,
    }
    with pytest.raises(ValueError, match="live_http"):
        mod.validate_handoff_payload(payload)
    payload["live_http_performed"] = False
    mod.validate_handoff_payload(payload)


def test_validate_handoff_rejects_unknown_keys_and_signals_extras(tmp_path: Path) -> None:
    mod = _load_handoff_module()
    payload = {
        "pytest_exit_code": 0,
        "pytest_stdout_tail": "",
        "signals_exit_code": 0,
        "signals_json": {"skipped_no_cache": 0, "raw_body": "x"},
        "daily_momentum_exit_code": 0,
        "investment_os_coverage_exit_code": 0,
        "investment_stdout_tail": "",
        "post_push_stdout_tail": "",
        "post_push_classification": "ok",
        "git_status_lines": "",
        "live_http_performed": False,
    }
    with pytest.raises(ValueError, match="extra_keys"):
        mod.validate_handoff_payload(payload)

    payload["signals_json"] = {"skipped_no_cache": 0}
    payload["evil_key"] = 1  # type: ignore[assignment]
    with pytest.raises(ValueError, match="unknown_keys"):
        mod.validate_handoff_payload(payload)


def test_validate_handoff_rejects_tail_control_chars() -> None:
    mod = _load_handoff_module()
    payload = {
        "pytest_exit_code": 0,
        "pytest_stdout_tail": "\x0012 passed\n",
        "signals_exit_code": 0,
        "signals_json": None,
        "daily_momentum_exit_code": 0,
        "investment_os_coverage_exit_code": 0,
        "investment_stdout_tail": "",
        "post_push_stdout_tail": "",
        "post_push_classification": "ok",
        "git_status_lines": "",
        "live_http_performed": False,
    }
    with pytest.raises(ValueError, match="tail_has_control_chars"):
        mod.validate_handoff_payload(payload)


def test_merge_logs_and_roundtrip_writes_json_md(tmp_path: Path) -> None:
    pytest_log = tmp_path / "pytest.log"
    signals_log = tmp_path / "sig.json"
    daily_log = tmp_path / "dm.log"
    inv_log = tmp_path / "inv.md"
    pp_log = tmp_path / "pp.log"
    git_log = tmp_path / "gst.log"
    payload_path = tmp_path / "manifest.json"

    pytest_log.write_text("\n...\n280 passed in 2.00s\n", encoding="utf-8")
    signals_log.write_text(
        json.dumps({"skipped_no_cache": 3, "mode": "x"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    daily_log.write_text("ok\n", encoding="utf-8")
    inv_log.write_text("# coverage\nintro\n", encoding="utf-8")
    pp_log.write_text("=== post-push-check ===\nLatest run:", encoding="utf-8")
    git_log.write_text(" M foo\n", encoding="utf-8")

    r_merge = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT_PY),
            "merge-logs",
            "--pytest-exit-code",
            "0",
            "--pytest-log",
            str(pytest_log),
            "--signals-exit-code",
            "0",
            "--signals-log",
            str(signals_log),
            "--daily-momentum-exit-code",
            "0",
            "--investment-log",
            str(inv_log),
            "--investment-exit-code",
            "0",
            "--post-push-log",
            str(pp_log),
            "--post-push-classification",
            "ok",
            "--git-status-log",
            str(git_log),
            "--out-json",
            str(payload_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r_merge.returncode == 0, r_merge.stderr

    merged = json.loads(payload_path.read_text(encoding="utf-8"))
    assert merged["signals_json"]["skipped_no_cache"] == 3
    py_load = merged["pytest_stdout_tail"]
    assert "280 passed" in py_load

    out_ops = tmp_path / "ops"
    r_write = subprocess.run(
        [sys.executable, str(_SCRIPT_PY), "write", "--from-json", str(payload_path), "--ops-dir", str(out_ops)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r_write.returncode == 0, r_write.stderr

    parsed = json.loads((out_ops / "latest_agent_handoff.json").read_text(encoding="utf-8"))
    assert parsed["pytest_count"] == 280
    assert parsed["skipped_no_cache"] == 3
    assert parsed["git_status_clean"] is False
    assert parsed["live_http_performed"] is False
    assert "signals-cache-only" in (out_ops / "latest_agent_handoff.md").read_text(encoding="utf-8")
