"""Main L gate: stale verdict prevention, fatal ops writes, jq-refresh downstream (no live HTTP).

Uses synthetic fixtures under tmp dirs; outputs/ops in repo must not be asserted as committed."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GATE_PY = _REPO_ROOT / "scripts" / "jq_ops_workflow_gate.py"
_JQ_LIVE_SH = _REPO_ROOT / "scripts" / "jq_watchlist_bars_cache_live.sh"
_JQ_REFRESH_SH = _REPO_ROOT / "scripts" / "jq_refresh_workflow.sh"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("jq_ops_workflow_gate", _GATE_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stderr_human_live_ops_summary(stderr: str) -> dict:
    for ln in stderr.splitlines():
        t = ln.strip()
        if not t.startswith("{"):
            continue
        try:
            d = json.loads(t)
        except json.JSONDecodeError:
            continue
        if d.get("mode") == "jquants_watchlist_cache_live":
            return d
    raise AssertionError(f"no human summary line in stderr: {stderr!r}")


def test_prepare_snapshots_removes_stale_latest(tmp_path: Path) -> None:
    mod = _load_gate_module()
    d = tmp_path / "ops"
    d.mkdir(parents=True)
    (d / "latest_verdict.json").write_text('{"verdict":"stale"}', encoding="utf-8")
    (d / "latest_ops_summary.json").write_text('{"mode":"x"}', encoding="utf-8")
    mod.prepare_snapshots(d)
    assert not (d / "latest_verdict.json").exists()
    assert not (d / "latest_ops_summary.json").exists()


def test_validate_missing_verdict_91(tmp_path: Path) -> None:
    mod = _load_gate_module()
    d = tmp_path / "ops"
    ec, msg = mod.validate_snapshots(d, date_from="2024-01-01", date_to="2024-02-02", codes=None)
    assert ec == 91
    assert "missing" in msg


def test_validate_passes_with_matching_summary(tmp_path: Path) -> None:
    mod = _load_gate_module()
    d = tmp_path / "ops"
    mod.write_test_fixture(d, fixture="pass", date_from="2024-02-17", date_to="2026-02-17", codes="5801,6504")
    ec, _msg = mod.validate_snapshots(d, date_from="2024-02-17", date_to="2026-02-17", codes="5801,6504")
    assert ec == 0


def test_codes_mismatch_raises_94(tmp_path: Path) -> None:
    mod = _load_gate_module()
    d = tmp_path / "ops"
    mod.write_test_fixture(d, fixture="pass", date_from="2024-02-17", date_to="2026-02-17", codes="5801,6504")
    ec, _msg = mod.validate_snapshots(d, date_from="2024-02-17", date_to="2026-02-17", codes="7011")
    assert ec == 94


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_watchlist_bars_cache_live_fatal_on_bad_ops_payload(tmp_path: Path) -> None:
    stub = tmp_path / "stub.json"
    stub.write_text("{bad-json", encoding="utf-8")
    ops_out = tmp_path / "opsout"
    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.update(
        {
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "7011",
            "TEST_JQ_LIVE_STUB_PAYLOAD": str(stub),
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )
    r = subprocess.run(["bash", str(_JQ_LIVE_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)
    assert r.returncode != 0


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_watchlist_bars_cache_live_ops_fatal_on_completed_shape_invalid(tmp_path: Path) -> None:
    """Completed-shape guard: CLI validation_error JSON must not emit latest_verdict.json."""
    ops_out = tmp_path / "opsout"
    stub = tmp_path / "stub_val_err.json"
    stub.write_text(
        json.dumps(
            {
                "status": "validation_error",
                "reason": "codes_csv_no_valid_wire_codes",
                "raw_response_included": False,
                "skipped_unsupported_code_tokens": ["%%%"],
            },
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.update(
        {
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "7011",
            "TEST_JQ_LIVE_STUB_PAYLOAD": str(stub),
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )
    r = subprocess.run(["bash", str(_JQ_LIVE_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)
    assert r.returncode == 3
    assert not (ops_out / "latest_verdict.json").exists()


def _write_fake_make(tmp_path: Path) -> tuple[Path, Path]:
    """bin/make that no-ops preview/live and logs signals-cache-only invocation."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True)
    log_file = tmp_path / "signals_ran.log"
    make_script = fake_bin / "make"
    log_esc = str(log_file).replace("'", "'\\''")
    make_script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"SIG_LOG='{log_esc}'\n"
        'if [[ "${1:-}" == "jq-cache-preview" ]] || [[ "${1:-}" == "jq-cache-live" ]]; then\n'
        "  exit 0\n"
        'fi\n'
        'if [[ "${1:-}" == "signals-cache-only" ]]; then\n'
        '  printf "signals-cache-only invoked\\n" > "$SIG_LOG"\n'
        "  exit 0\n"
        'fi\n'
        'echo "fake-make: unexpected target ${1:-}" >&2\n'
        "exit 99\n",
        encoding="utf-8",
    )
    os.chmod(make_script, 0o755)
    return fake_bin, log_file


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_refresh_codes_only_stub_pass_invokes_signals_no_empty_make_argv(tmp_path: Path) -> None:
    fake_bin, log_file = _write_fake_make(tmp_path)
    ops_out = tmp_path / "jq_ops"
    ops_out.mkdir(parents=True)

    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.pop("ALLOW_PARTIAL_CACHE", None)
    env.update(
        {
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "TEST_JQ_REFRESH_GATE_STUB": "pass",
            "TEST_JQ_REFRESH_SKIP_DAILY": "1",
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "5801,6504",
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )

    r = subprocess.run(["bash", str(_JQ_REFRESH_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)

    assert r.returncode == 0, r.stderr + r.stdout
    txt = log_file.read_text(encoding="utf-8")
    assert "signals-cache-only invoked" in txt


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_refresh_omit_verdict_exits_gate(tmp_path: Path) -> None:
    fake_bin, _ = _write_fake_make(tmp_path)
    ops_out = tmp_path / "jq_ops_empty"
    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.update(
        {
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "TEST_JQ_REFRESH_GATE_STUB": "omit_verdict",
            "TEST_JQ_REFRESH_SKIP_DAILY": "1",
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "7011",
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )
    r = subprocess.run(["bash", str(_JQ_REFRESH_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert r.returncode >= 91 or "missing latest_verdict" in (r.stderr + r.stdout)


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_refresh_partial_requires_allow_partial(tmp_path: Path) -> None:
    fake_bin, log_file = _write_fake_make(tmp_path)
    ops_out = tmp_path / "jq_ops_p"
    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.pop("ALLOW_PARTIAL_CACHE", None)
    env.update(
        {
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "TEST_JQ_REFRESH_GATE_STUB": "partial_success",
            "TEST_JQ_REFRESH_SKIP_DAILY": "1",
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "7011",
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )
    r = subprocess.run(["bash", str(_JQ_REFRESH_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)
    assert r.returncode != 0
    assert not log_file.exists() or log_file.stat().st_size == 0

    env2 = dict(env)
    env2["ALLOW_PARTIAL_CACHE"] = "true"
    r2 = subprocess.run(["bash", str(_JQ_REFRESH_SH)], cwd=str(_REPO_ROOT), env=env2, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr + r2.stdout


def test_print_live_ops_human_json_line(tmp_path: Path) -> None:
    mod = _load_gate_module()
    d = tmp_path / "ops"
    d.mkdir(parents=True)
    mod.write_test_fixture(d, fixture="fail", date_from="2024-02-17", date_to="2026-02-17", codes="7011")

    import io

    buf = io.StringIO()
    old_err = sys.stderr
    sys.stderr = buf
    try:
        assert mod.print_live_ops_human_summary(d) == 0
    finally:
        sys.stderr = old_err

    blob = json.loads(buf.getvalue().strip())
    assert blob["verdict"] == "fail"
    assert blob["reason"]
    assert "success_count" in blob
    assert blob.get("raw_response_included") is False


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_watchlist_bars_cache_live_stub_prints_human_summary_on_stderr(tmp_path: Path) -> None:
    ops_out = tmp_path / "opsout_h"
    stub = tmp_path / "ok_live.json"
    stub.write_text(
        json.dumps(
            {
                "status": "completed",
                "mode": "jquants_watchlist_cache_live",
                "target_count": 1,
                "success_count": 1,
                "error_count": 0,
                "skipped_count": 0,
                "cache_written_count": 1,
                "failed_codes": [],
                "results": [{"code": "7011", "status": "success", "raw_response_included": False}],
                "live_http_performed": True,
                "raw_response_included": False,
                "date_from": "2024-02-17",
                "date_to": "2026-02-17",
                "codes_requested": "7011",
            },
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.update(
        {
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "7011",
            "TEST_JQ_LIVE_STUB_PAYLOAD": str(stub),
            "TEST_JQ_LIVE_CLI_EXIT": "1",
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )
    r = subprocess.run(["bash", str(_JQ_LIVE_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)
    assert r.returncode == 1
    line = _stderr_human_live_ops_summary(r.stderr)
    assert line["verdict"] == "pass"
    assert line["error_count"] == 0


@pytest.mark.skipif(sys.platform.startswith("win"), reason="requires POSIX bash")
def test_jq_refresh_stub_partial_prints_human_summary_on_stderr(tmp_path: Path) -> None:
    fake_bin, _log = _write_fake_make(tmp_path)
    ops_out = tmp_path / "jq_ops_human"
    env = dict(os.environ)
    env.pop("LIMIT", None)
    env.pop("ALLOW_PARTIAL_CACHE", None)
    env.update(
        {
            "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
            "ALLOW_TEST_JQ_STUBS": "YES",
            "JQ_OPS_OUTPUT_DIR": str(ops_out),
            "TEST_JQ_REFRESH_GATE_STUB": "partial_success",
            "TEST_JQ_REFRESH_SKIP_DAILY": "1",
            "CONFIRM_LIVE_HTTP": "YES",
            "FROM": "2024-02-17",
            "TO": "2026-02-17",
            "CODES": "7011",
            "PYTHON": sys.executable,
            "HOME": env.get("HOME", str(tmp_path)),
        },
    )
    r = subprocess.run(["bash", str(_JQ_REFRESH_SH)], cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True)
    assert r.returncode != 0
    tail = _stderr_human_live_ops_summary(r.stderr)
    assert tail["verdict"] == "partial_success"
