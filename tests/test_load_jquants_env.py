"""Tests for scripts/load_jquants_env.py (Hotfix C — safe .env parsing)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_LOAD_SCRIPT = ROOT / "scripts" / "load_jquants_env.py"


def _load_parser_module():
    spec = importlib.util.spec_from_file_location("_load_jquants_env", _LOAD_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_keeps_command_substitution_literal(tmp_path: Path) -> None:
    mod = _load_parser_module()
    p = tmp_path / ".env"
    p.write_text(
        "JQUANTS_API_KEY=$(echo bad)\n"
        "JQUANTS_ENABLED=true\n",
        encoding="utf-8",
    )
    d = mod.parse_jquants_env_file(p)
    assert d["JQUANTS_API_KEY"] == "$(echo bad)"
    assert d["JQUANTS_ENABLED"] == "true"


def test_parse_export_prefix_and_comments(tmp_path: Path) -> None:
    mod = _load_parser_module()
    p = tmp_path / ".env"
    p.write_text(
        "# comment\n"
        "\n"
        'export JQUANTS_API_KEY="x"\n'
        "JQUANTS_ENABLED=false\n",
        encoding="utf-8",
    )
    d = mod.parse_jquants_env_file(p)
    assert d["JQUANTS_ENABLED"] == "false"
    assert d["JQUANTS_API_KEY"] == "x"


def test_parse_disallows_unknown_keys(tmp_path: Path) -> None:
    mod = _load_parser_module()
    p = tmp_path / ".env"
    p.write_text("FOO=bar\nJQUANTS_ENABLED=1\n", encoding="utf-8")
    d = mod.parse_jquants_env_file(p)
    assert "FOO" not in d
    assert d["JQUANTS_ENABLED"] == "1"


def test_doctor_mode_prints_no_secret_values(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    secret = "NEVER_PRINT_THIS_SECRET_12345"
    p.write_text(f"JQUANTS_API_KEY={secret}\nJQUANTS_ENABLED=true\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_LOAD_SCRIPT), "doctor", "--env-file", str(p)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert secret not in out
    assert "NEVER_PRINT" not in out
    assert "JQUANTS_API_KEY: present (value hidden)" in out
    assert "JQUANTS_ENABLED: true" in out


def test_run_mode_passes_enabled_to_child(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("JQUANTS_ENABLED=true\n", encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            str(_LOAD_SCRIPT),
            "run",
            "--env-file",
            str(p),
            "--",
            sys.executable,
            "-c",
            'import os, json; print(json.dumps(os.environ.get("JQUANTS_ENABLED")))',
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout.strip()) == "true"


def test_run_sets_data_availability_in_child_for_guard(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text(
        "JQUANTS_DATA_AVAILABLE_FROM=2024-02-17\n"
        "JQUANTS_DATA_AVAILABLE_TO=2026-02-17\n",
        encoding="utf-8",
    )
    code = (
        "from invis_alpha_os.data.adapters.jquants_client import "
        "jquants_data_availability_bounds_from_env; "
        "print(jquants_data_availability_bounds_from_env()[0] is not None)"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(_LOAD_SCRIPT),
            "run",
            "--env-file",
            str(p),
            "--",
            sys.executable,
            "-c",
            code,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "True"


def test_jquants_smoke_dry_run_yields_dry_run_status(tmp_path: Path) -> None:
    """Smoke script must load .env without shell source so JQUANTS_ENABLED applies."""
    p = tmp_path / ".env"
    p.write_text(
        "JQUANTS_ENABLED=true\n"
        "JQUANTS_API_BASE_URL=https://api.jquants.com/v2\n"
        "JQUANTS_API_KEY=dummy\n",
        encoding="utf-8",
    )
    # Use temp .env via env — script uses ROOT/.env; copy for repo root is unsafe.
    # Instead call CLI the same way the shell script does, with explicit --env-file:
    proc = subprocess.run(
        [
            sys.executable,
            str(_LOAD_SCRIPT),
            "run",
            "--env-file",
            str(p),
            "--",
            sys.executable,
            "-m",
            "invis_alpha_os.cli.main",
            "debug",
            "jquants-watchlist-bars",
            "--date",
            "2024-02-19",
            "--limit",
            "3",
            "--save-summary",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0
    assert '"status": "dry_run"' in proc.stdout


def test_ops_scripts_do_not_source_dotenv_file() -> None:
    for name in ("env_doctor.sh", "jquants_smoke.sh", "daily_check.sh"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert 'source "${ROOT}/.env"' not in text
        assert "source .env" not in text
