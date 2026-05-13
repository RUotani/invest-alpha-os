"""Main R1: US daily bars fixture import CLI (no HTTP)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_daily_bars_cache as usc
from invis_alpha_os.reports.momentum_daily import render_us_momentum_cache_only_section
from invis_alpha_os.signals.momentum import load_bars_json_file

REPO_ROOT = Path(__file__).resolve().parents[1]
FIX = REPO_ROOT / "tests" / "fixtures" / "us_daily_bars"
runner = CliRunner()


_REQUIRED_KEYS = frozenset({"date", "open", "high", "low", "close", "volume"})


@pytest.mark.parametrize(
    "name",
    ["MSFT", "GOOGL", "GLDM"],
)
def test_us_daily_fixture_json_is_valid_sanitized_bar_list(name: str) -> None:
    bars = load_bars_json_file(FIX / f"{name}.json")
    assert len(bars) >= 21, name
    for row in bars:
        assert _REQUIRED_KEYS == set(row.keys()), name
        assert str(row["date"]).strip()


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("US cache import tests must not use live HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)


def test_us_cache_import_dry_run_does_not_write_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    msft = FIX / "MSFT.json"
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-import",
            "--symbol",
            "MSFT",
            "--bars-file",
            str(msft),
            "--asset-class",
            "us_equity",
            "--source",
            "local_fixture",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    summary = json.loads(r.stdout.strip())
    assert summary["status"] == "dry_run"
    assert summary["live_http"] is False
    assert summary["raw_response_included"] is False
    assert summary["bar_count"] == len(load_bars_json_file(msft))
    sanitized = json.dumps(summary).replace("raw_response_included", "")
    lowsan = sanitized.lower()
    forbidden = ("raw_response", "api_key", "authorization", "bearer")
    assert not any(x in lowsan for x in forbidden)
    assert not (tmp_path / "market_data" / "us_daily_bars" / "MSFT.json").is_file()


def test_us_cache_import_write_cache_persists_sanitized_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    msft = FIX / "MSFT.json"
    r = runner.invoke(
        app,
        [
            "debug",
            "us-daily-bars-cache-import",
            "--symbol",
            "MSFT",
            "--bars-file",
            str(msft),
            "--asset-class",
            "us_equity",
            "--source",
            "local_fixture",
            "--write-cache",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    summary = json.loads(r.stdout.strip())
    assert summary["status"] == "success"
    assert summary["live_http"] is False
    assert summary["raw_response_included"] is False
    assert summary["cache_written_to"] == "outputs/market_data/us_daily_bars/MSFT.json"

    path = tmp_path / "market_data" / "us_daily_bars" / "MSFT.json"
    assert path.is_file()
    blob = path.read_text(encoding="utf-8").lower()
    for tok in ("raw_response", "api_key", "authorization", "bearer"):
        assert tok not in blob

    loaded = usc.load_us_daily_bars_cache("MSFT")
    assert loaded is not None
    bars, meta = loaded
    assert len(bars) == summary["bar_count"]
    assert meta.get("source") == "local_fixture"


def test_us_cache_import_invalid_bars_json_uses_sanitized_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text(
        '[{"date":"2024-01-02","open":"super_secret_xyz","high":1,"low":1,"close":1,"volume":1}]',
        encoding="utf-8",
    )
    r = runner.invoke(
        app,
        ["debug", "us-daily-bars-cache-import", "--symbol", "MSFT", "--bars-file", str(bad)],
    )
    assert r.exit_code == 2
    assert "super_secret" not in r.stderr
    summary = json.loads(r.stderr.strip())
    assert summary["reason"] == "bars_parse_failed"
    assert "super_secret" not in json.dumps(summary)


def test_makefile_lists_us_cache_targets() -> None:
    makefile = REPO_ROOT / "Makefile"
    m = makefile.read_text(encoding="utf-8")
    assert "us-cache-fixture-import:" in m
    assert "us-momentum-check:" in m
    assert re.search(r"\.PHONY:.*us-momentum-check", m, flags=re.DOTALL)


def test_us_momentum_section_renders_from_cache_after_fixture_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(usc, "OUTPUTS_DIR", tmp_path)
    for sym, ac in (("MSFT", "us_equity"), ("GOOGL", "us_equity"), ("GLDM", "us_etf")):
        r = runner.invoke(
            app,
            [
                "debug",
                "us-daily-bars-cache-import",
                "--symbol",
                sym,
                "--bars-file",
                str(FIX / f"{sym}.json"),
                "--asset-class",
                ac,
                "--source",
                "local_fixture",
                "--write-cache",
            ],
        )
        assert r.exit_code == 0, r.stdout + r.stderr

    txt = render_us_momentum_cache_only_section()
    assert "## Momentum Signals — US Cache Only" in txt
    assert "| MSFT |" in txt and "| GOOGL |" in txt and "| GLDM |" in txt
    assert "**Bars source:** `cache` — **US**" in txt
