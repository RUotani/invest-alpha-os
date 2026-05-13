"""Main R3: gated Stooq one-symbol live preview (shape digest only; no cache write)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from urllib.error import HTTPError

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_provider_live_preview as uplp
from invis_alpha_os.data.us_provider_live_preview import stooq_live_preview_shape_digest

REPO = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _tiny_stooq_csv_body() -> bytes:
    csv = (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-06-03,410,412,408,411,900000\n"
        "2024-06-04,411,413,410,412,910000\n"
    )
    return csv.encode("utf-8")


def _patch_urlopen_ok(mock_urlopen: MagicMock, body: bytes) -> None:
    resp = MagicMock()
    resp.getcode.return_value = 200
    resp.read.return_value = body

    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = None

    mock_urlopen.return_value = cm


@pytest.fixture(autouse=True)
def _clear_confirm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, raising=False)


def test_dry_run_shape_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[object] = []

    def _fail(*args: object, **kwargs: object) -> None:
        called.append(True)
        pytest.fail("urlopen must not be called when live=False")

    monkeypatch.setattr(uplp, "urlopen", _fail)

    out = stooq_live_preview_shape_digest(" MSFT ", live=False)
    assert called == []
    assert out["status"] == "dry_run"
    assert out["live_http_performed"] is False
    assert out["raw_response_included"] is False
    assert out["symbol"] == "MSFT"


def test_cli_dry_run_does_not_call_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("CLI dry-run must not open HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)

    r = runner.invoke(
        app,
        ["debug", "us-provider-live-preview", "--symbol", "MSFT", "--provider", "stooq_preview"],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "dry_run"
    assert payload["live_http_performed"] is False


def test_live_without_confirm_validation_error_exit_2_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("HTTP must not run without CONFIRM_US_LIVE_HTTP=YES")

    monkeypatch.setattr(uplp, "urlopen", _boom)

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-live-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "validation_error"
    assert payload["reason"] == "live_http_not_confirmed"
    assert payload["live_http_performed"] is False


@patch.object(uplp, "urlopen")
def test_live_success_cli_shape_digest(mock_urlopen: MagicMock) -> None:
    _patch_urlopen_ok(mock_urlopen, _tiny_stooq_csv_body())
    env = uplp.CONFIRM_US_LIVE_HTTP_ENV

    with patch.dict(os.environ, {env: "YES"}, clear=False):
        r = runner.invoke(
            app,
            [
                "debug",
                "us-provider-live-preview",
                "--symbol",
                "MSFT",
                "--provider",
                "stooq_preview",
                "--live",
            ],
        )

    assert r.exit_code == 0, r.stdout + r.stderr
    payload = json.loads(r.stdout.strip())
    assert payload["status"] == "live_preview_ok"
    assert payload["row_count"] == 2
    assert payload["first_date"] == "2024-06-03"
    assert payload["last_date"] == "2024-06-04"
    assert payload["columns"] == ["Date", "Open", "High", "Low", "Close", "Volume"]
    assert payload["raw_response_included"] is False
    assert payload["cache_write_performed"] is False
    assert payload["live_http_performed"] is True


def test_live_success_stdout_has_no_sensitive_substrings(monkeypatch: pytest.MonkeyPatch) -> None:
    body = (
        _tiny_stooq_csv_body()
        .decode("utf-8")
        .replace("Volume", "V")  # keep parseable CSV; avoid substring false positives below
        .encode("utf-8")
    )
    mock_open = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value.getcode.return_value = 200
    cm.__enter__.return_value.read.return_value = body
    cm.__exit__.return_value = None
    mock_open.return_value = cm
    monkeypatch.setattr(uplp, "urlopen", mock_open)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-live-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--live",
        ],
    )

    assert r.exit_code == 0, r.stdout + r.stderr
    low = r.stdout.lower()
    # Required flag `raw_response_included` contains the substring raw_response — do not forbid it outright.
    for frag in ("api_key", "authorization", "bearer"):
        assert frag not in low


def test_http_error_payload_has_no_response_body(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise HTTPError(
            url="http://example.invalid/q/d/l/?dummy=1",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(uplp, "urlopen", _raise)
    monkeypatch.setenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, "YES")

    payload = stooq_live_preview_shape_digest("MSFT", live=True)
    dumped = json.dumps(payload, ensure_ascii=False)
    assert payload["status"] == "http_error"
    assert payload["http_status"] == 404
    assert payload.get("reason") == "http_status_404"
    assert "csv" not in dumped.lower()
    assert "volume" not in dumped.lower()
    assert "411" not in dumped
    assert payload["raw_response_included"] is False


def test_makefile_contains_main_r3_targets() -> None:
    makefile = REPO / "Makefile"
    m = makefile.read_text(encoding="utf-8")
    assert "\nus-provider-live-preview-dry-run:" in m or m.startswith("us-provider-live-preview-dry-run:")
    assert (
        "\nus-provider-live-preview-stooq:" in m or m.startswith("us-provider-live-preview-stooq:")
    )
    assert ".PHONY" in m and "us-provider-live-preview-dry-run" in m


def test_unsupported_provider_exit_2() -> None:
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-live-preview",
            "--symbol",
            "MSFT",
            "--provider",
            "alpha_vantage_preview",
            "--live",
        ],
    )
    assert r.exit_code == 2
    p = json.loads(r.stdout.strip())
    assert p["status"] == "validation_error"


def test_live_stooq_make_target_not_in_safe_push_recipe() -> None:
    """Optional live Makefile target stays operator-only (not chained into safe-push)."""
    makefile = (REPO / "Makefile").read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(makefile):
        if ln.startswith("safe-push:"):
            tail = "\n".join(makefile[i : i + 15])
            assert "us-provider-live-preview-stooq" not in tail
            return
    pytest.fail("Makefile missing safe-push target")
