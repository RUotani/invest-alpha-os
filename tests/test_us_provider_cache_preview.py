"""Main R4: gated Stooq parse + optional cache (CLI); tests never hit live HTTP."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from urllib.error import HTTPError

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_daily_bars_cache as usc
from invis_alpha_os.data import us_provider_live_preview as uplp

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _csv_body() -> bytes:
    return (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-06-03,410,412,408,411,900000\n"
        "2024-06-04,411,413,410,412,910000\n"
    ).encode("utf-8")


def _patch_urlopen_ok(mock_urlopen: MagicMock, body: bytes) -> None:
    resp = MagicMock()
    resp.getcode.return_value = 200
    resp.read.return_value = body
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = None
    mock_urlopen.return_value = cm


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, raising=False)
    monkeypatch.delenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, raising=False)


def test_cli_dry_run_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("dry-run must not open HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)

    r = runner.invoke(
        app,
        ["debug", "us-provider-cache-preview", "--symbol", "MSFT", "--provider", "stooq_preview"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["status"] == "dry_run"
    assert p["live_http_performed"] is False
    assert p["cache_write_performed"] is False


def test_cli_live_without_confirm_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("live without confirm")

    monkeypatch.setattr(uplp, "urlopen", _boom)

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "live_http_not_confirmed"


def test_cli_write_cache_without_env_no_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)

    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("blocked cache gate must skip HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
            "--write-cache",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["reason"] == "cache_write_not_confirmed"
    assert not list(tmp_path.rglob("MSFT.json"))


@patch.object(uplp, "urlopen")
def test_live_preview_ok_shape_no_raw_prices_in_payload_checks(mock_urlopen: MagicMock) -> None:
    _patch_urlopen_ok(mock_urlopen, _csv_body())
    with patch.dict(os.environ, {uplp.CONFIRM_US_LIVE_HTTP_ENV: "YES"}, clear=False):
        r = runner.invoke(
            app,
            [
                "debug",
                "us-provider-cache-preview",
                "--symbol",
                "MSFT",
                "--provider",
                "stooq_preview",
                "--live",
            ],
        )
    assert r.exit_code == 0, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["status"] == "preview_ok"
    assert p["row_count"] == 2
    assert p["first_date"] == "2024-06-03"
    assert p["last_date"] == "2024-06-04"
    assert p["raw_response_included"] is False


def test_live_write_cache_persists_sanitized_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    mock_open = MagicMock()
    resp = MagicMock()
    resp.getcode.return_value = 200
    resp.read.return_value = _csv_body()
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = None
    mock_open.return_value = cm
    monkeypatch.setattr(uplp, "urlopen", mock_open)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, "YES")

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
            "--write-cache",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["status"] == "success"
    assert p["cache_write_performed"] is True
    out = tmp_path / "market_data" / "us_daily_bars" / "MSFT.json"
    assert out.is_file()
    blob = json.loads(out.read_text(encoding="utf-8"))
    assert blob["source"] == "stooq_preview_gated_live"
    assert blob["bar_count"] == 2
    assert len(blob["bars"]) == 2
    low = json.dumps(blob).lower()
    for frag in ("api_key", "authorization", "bearer"):
        assert frag not in low


def test_http_error_no_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise HTTPError("http://e/", 503, "Svc", hdrs=None, fp=None)

    monkeypatch.setattr(uplp, "urlopen", _raise)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
        ],
    )
    assert r.exit_code == 1, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["status"] == "http_error"
    assert p.get("http_status") == 503
    dumped = json.dumps(p).lower()
    assert "svc" not in dumped
    assert "<html" not in dumped
    assert p["raw_response_included"] is False


@patch.object(uplp, "urlopen")
def test_parse_error_headerless_row_diagnostics_hide_numeric_cells(mock_urlopen: MagicMock) -> None:
    body = "2024-01-02,100.0,110.0,90.0,105.0,1234567\n"
    _patch_urlopen_ok(mock_urlopen, body.encode("utf-8"))
    with patch.dict(os.environ, {uplp.CONFIRM_US_LIVE_HTTP_ENV: "YES"}, clear=False):
        r = runner.invoke(
            app,
            [
                "debug",
                "us-provider-cache-preview",
                "--symbol",
                "MSFT",
                "--provider",
                "stooq_preview",
                "--live",
            ],
        )

    assert r.exit_code == 1, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    dj = json.dumps(p["response_diagnostics"], ensure_ascii=False)
    assert "2024" not in dj
    assert "100.0" not in dj
    assert "1234567" not in dj


@patch.object(uplp, "urlopen")
def test_parse_error_payload_has_safe_diagnostics_not_raw_cells(mock_urlopen: MagicMock) -> None:
    body = "Ticker,Px,ExtraColumn\nMSFT,123,filler\n"
    _patch_urlopen_ok(mock_urlopen, body.encode("utf-8"))
    with patch.dict(os.environ, {uplp.CONFIRM_US_LIVE_HTTP_ENV: "YES"}, clear=False):
        r = runner.invoke(
            app,
            [
                "debug",
                "us-provider-cache-preview",
                "--symbol",
                "MSFT",
                "--provider",
                "stooq_preview",
                "--live",
            ],
        )

    assert r.exit_code == 1, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["status"] == "parse_error"
    assert "response_diagnostics" in p
    assert p["raw_response_included"] is False

    dumped = json.dumps(p, ensure_ascii=False).lower()
    assert "123" not in dumped

    diag = p["response_diagnostics"]
    assert isinstance(diag, dict)
    assert set(diag).issuperset(
        {
            "body_kind",
            "header_columns_sanitized",
            "header_column_count",
            "line_count_limited",
            "has_required_columns",
            "required_columns_missing",
            "delimiter_guess",
        },
    )

    dj = json.dumps(diag).lower()
    for needle in ("raw_response", "api_key", "authorization", "bearer"):
        assert needle not in dj
    assert "123" not in dj


def test_makefile_has_r4_targets() -> None:
    m = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "us-provider-cache-preview-dry-run:" in m
    assert "us-provider-cache-preview-stooq:" in m
    assert "us-provider-cache-write-stooq:" in m
    assert ".PHONY" in m and "us-provider-cache-preview-dry-run" in m


def test_r4_live_targets_not_chained_under_safe_push() -> None:
    lines = (REPO / "Makefile").read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("safe-push:"):
            tail = "\n".join(lines[i : i + 20])
            for needle in ("us-provider-cache-preview-stooq", "us-provider-cache-write-stooq"):
                assert needle not in tail
            return
    pytest.fail("Makefile missing safe-push")


def test_success_stdout_sensitive_tokens_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    mock_open = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value.getcode.return_value = 200
    cm.__enter__.return_value.read.return_value = _csv_body()
    cm.__exit__.return_value = None
    mock_open.return_value = cm
    monkeypatch.setattr(uplp, "urlopen", mock_open)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")
    monkeypatch.setenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, "YES")

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
            "--write-cache",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    low = r.stdout.lower()
    for frag in ("api_key", "authorization", "bearer"):
        assert frag not in low
