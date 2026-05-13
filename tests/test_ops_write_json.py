"""ops_write_json: local summary files (no secrets; default path gitignored)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _load_ops_write_json_module(repo: Path):
    script = repo / "scripts" / "ops_write_json.py"
    spec = importlib.util.spec_from_file_location("ops_write_json_runner", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ops_write_json_pytest_mode(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "ops_write_json.py"
    r = subprocess.run(
        [sys.executable, str(script), "--mode", "pytest", "--pytest-exit", "0", "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    s = json.loads((tmp_path / "latest_ops_summary.json").read_text(encoding="utf-8"))
    v = json.loads((tmp_path / "latest_verdict.json").read_text(encoding="utf-8"))
    assert s["schema_version"] == 1
    assert s["mode"] == "pytest"
    assert s["pytest_exit_code"] == 0
    assert s["pytest_passed"] is True
    assert s["live_http_performed"] is False
    assert v["verdict"] == "pass"


def test_verdict_jquants_pass_partial_fail_human() -> None:
    repo = Path(__file__).resolve().parents[1]
    mod = _load_ops_write_json_module(repo)
    vf = mod.verdict_jquants_watchlist_cache_live
    assert vf({"error_count": 0, "success_count": 2, "cache_written_count": 2, "results": []})[0] == "pass"
    assert vf({"error_count": 0, "success_count": 0, "cache_written_count": 0, "results": []})[0] == "fail"
    assert vf({"error_count": 1, "success_count": 2, "cache_written_count": 2, "results": [{}, {}]})[0] == "partial_success"
    assert vf({"error_count": 2, "success_count": 0, "cache_written_count": 0, "results": []})[0] == "fail"
    assert (
        vf(
            {
                "error_count": 0,
                "success_count": 1,
                "cache_written_count": 0,
                "results": [{"status": "success"}],
            }
        )[0]
        == "partial_success"
    )
    assert (
        vf(
            {
                "error_count": 0,
                "success_count": 1,
                "cache_written_count": 1,
                "results": [{"status": "http_error", "reason": "http_error_unknown"}],
            }
        )[0]
        == "needs_human_review"
    )


def test_ops_jquants_watchlist_cache_live_payload(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "ops_write_json.py"
    payload = {
        "status": "completed",
        "target_count": 2,
        "success_count": 2,
        "error_count": 0,
        "skipped_count": 0,
        "cache_written_count": 2,
        "failed_codes": [],
        "results": [
            {
                "code": "7011",
                "status": "success",
                "row_count": 10,
                "sanitized_bar_count": 10,
                "cache_written_to": "data/x.json",
                "raw_response_included": False,
                "trace_id": "not-in-ops-summary",
            },
            {"code": "7203", "status": "success"},
        ],
        "live_http_performed": True,
        "raw_response_included": False,
        "date_from": "2024-01-01",
        "date_to": "2024-01-10",
        "codes_requested": "5801,6504",
    }
    p = tmp_path / "p.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), "--mode", "jquants_watchlist_cache_live", "--payload-file", str(p), "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    s = json.loads((tmp_path / "latest_ops_summary.json").read_text(encoding="utf-8"))
    v = json.loads((tmp_path / "latest_verdict.json").read_text(encoding="utf-8"))
    assert s["mode"] == "jquants_watchlist_cache_live"
    assert s["live_http_performed"] is True
    assert s["raw_response_included"] is False
    assert s["failed_codes"] == []
    assert s["codes_requested"] == "5801,6504"
    assert v["verdict"] == "pass"
    rows = s["results"]
    assert rows[0]["code"] == "7011"
    assert rows[0]["row_count"] == 10
    assert rows[0]["sanitized_bar_count"] == 10
    assert rows[0]["cache_written_to"] == "data/x.json"
    assert rows[0]["raw_response_included"] is False
    assert "trace_id" not in rows[0]


def test_ops_jquants_rejects_validation_error_payload(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "ops_write_json.py"
    payload = {"status": "validation_error", "reason": "codes_csv_no_valid_wire_codes", "raw_response_included": False}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), "--mode", "jquants_watchlist_cache_live", "--payload-file", str(p), "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3
    assert not (tmp_path / "latest_verdict.json").exists()


def test_ops_jquants_rejects_forbidden_error_kind(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "ops_write_json.py"
    payload = {
        "status": "completed",
        "mode": "jquants_watchlist_cache_live",
        "target_count": 1,
        "success_count": 0,
        "error_count": 1,
        "skipped_count": 0,
        "cache_written_count": 0,
        "failed_codes": ["7011"],
        "results": [{"code": "7011", "status": "http_error", "reason": "x", "error_kind": "http_error"}],
        "live_http_performed": True,
        "raw_response_included": False,
        "date_from": "2024-01-01",
        "date_to": "2024-01-10",
    }
    p = tmp_path / "bad_kind.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), "--mode", "jquants_watchlist_cache_live", "--payload-file", str(p), "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3


def test_ops_jquants_rejects_forbidden_row_field(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "ops_write_json.py"
    payload = {
        "status": "completed",
        "mode": "jquants_watchlist_cache_live",
        "target_count": 1,
        "success_count": 1,
        "error_count": 0,
        "skipped_count": 0,
        "cache_written_count": 1,
        "failed_codes": [],
        "results": [{"code": "7011", "status": "success", "error_body_preview": "oops"}],
        "live_http_performed": True,
        "raw_response_included": False,
        "date_from": "2024-01-01",
        "date_to": "2024-01-10",
    }
    p = tmp_path / "badrow.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(script), "--mode", "jquants_watchlist_cache_live", "--payload-file", str(p), "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 3
