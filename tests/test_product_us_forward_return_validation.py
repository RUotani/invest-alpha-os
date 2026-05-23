"""Product P5: US forward-return validation (cache-only)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from invis_alpha_os.observation.service import ObservationService
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.product.us_forward_return_validation import (
    compute_us_forward_returns,
    format_us_forward_return_markdown,
    parse_positive_horizons,
)
from invis_alpha_os.signals.momentum import load_bars_json_file

REPO = Path(__file__).resolve().parents[1]
FIX_MSFT = REPO / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


@pytest.fixture(autouse=True)
def _block_urlopen(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no HTTP")))


@pytest.fixture
def obs_and_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    cache_dir = tmp_path / "us_daily_bars"
    cache_dir.mkdir()
    outputs = tmp_path / "outputs"
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)

    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-23T12:00:00+00:00",
        generated_at="2026-05-23T12:00:05+00:00",
    )
    saved = usc.us_daily_bars_cache_path("MSFT")
    dest = cache_dir / "MSFT.json"
    dest.write_text(saved.read_text(encoding="utf-8"), encoding="utf-8")

    note = (
        "us_cache_signal observation_only status=ok momentum_label=uptrend "
        "not buy/sell advice"
    )
    svc = ObservationService(observation_path=obs_path, outcome_path=outputs / "outcome.jsonl")
    row = svc.log_observation("MSFT", note)
    obs_path.write_text(
        json.dumps(
            {
                "id": row.id,
                "created_at": f"{event_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": note,
                "evidence_ids": [],
                "tags": [],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return obs_path, cache_dir


def test_forward_returns_computed(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(
        observation_path=obs_path,
        cache_dir=cache_dir,
        horizons=(5, 20),
    )
    assert report["rows_matched"] == 1
    assert report["rows_considered"] == 1
    ex = report["examples"][0]
    assert ex["horizons"]["5"] is not None
    assert ex["horizons"]["20"] is not None


def test_insufficient_future_bars_skipped(tmp_path: Path, obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    bars = load_bars_json_file(FIX_MSFT)
    last_date = bars[-1]["date"][:10]
    obs_path.write_text(
        obs_path.read_text(encoding="utf-8").strip()
        + "\n"
        + json.dumps(
            {
                "id": "x2",
                "created_at": f"{last_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": "us_cache_signal observation_only status=ok momentum_label=uptrend not buy/sell advice",
                "evidence_ids": [],
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = compute_us_forward_returns(
        observation_path=obs_path,
        cache_dir=cache_dir,
        horizons=(60,),
    )
    assert report["rows_skipped"] >= 1
    assert report["skipped_reasons"].get("insufficient_future_bars", 0) >= 1


def test_invalid_jsonl_fail_closed(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    obs_path.write_text("{ not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSONL"):
        compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)


def test_missing_observation_log(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compute_us_forward_returns(
            observation_path=tmp_path / "missing.jsonl",
            cache_dir=tmp_path,
        )


def test_markdown_contains_caution(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    md = format_us_forward_return_markdown(report)
    assert "not buy/sell advice" in md.lower() or "not buy/sell" in md.lower()
    assert "observation only" in md.lower()
    assert "sample quality" in md.lower()


def test_parse_horizons_positive_only() -> None:
    assert parse_positive_horizons("5,20") == (5, 20)
    with pytest.raises(ValueError, match="positive"):
        parse_positive_horizons("0,5")
    with pytest.raises(ValueError, match="positive"):
        parse_positive_horizons("-5")
    with pytest.raises(ValueError, match="empty"):
        parse_positive_horizons("")
    with pytest.raises(ValueError, match="integer"):
        parse_positive_horizons("5,abc")


def test_sample_quality_empty(tmp_path: Path) -> None:
    obs = tmp_path / "obs.jsonl"
    obs.write_text(
        '{"id":"1","created_at":"2026-01-01T00:00:00+00:00","symbol":"MSFT",'
        '"note":"other row","evidence_ids":[],"tags":[]}\n',
        encoding="utf-8",
    )
    report = compute_us_forward_returns(observation_path=obs, cache_dir=tmp_path)
    assert report["sample_quality"]["status"] == "empty"


def test_sample_quality_thin(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    assert report["sample_quality"]["status"] == "thin"
    assert report["rows_matched"] == 1


def test_hit_rate_buckets(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(5,)
    )
    bucket = report["quality_buckets"]["global"]["5"]
    assert bucket["count"] == 1
    assert bucket["hit_rate_positive"] in (0.0, 1.0)
    assert bucket["best"] is not None


def test_cli_invalid_horizons_exit_2() -> None:
    result = CliRunner().invoke(
        app,
        ["validate", "us-forward-returns", "--horizons", "0", "--format", "json"],
    )
    assert result.exit_code == 2
    assert "positive" in (result.stderr or result.stdout).lower()
