"""Product P5: US forward-return validation (cache-only)."""

from __future__ import annotations

import json
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


def test_stale_skip_by_symbol_list(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    assert isinstance(report.get("stale_skip_by_symbol"), list)


def test_format_markdown_includes_stale_skip_symbols() -> None:
    from invis_alpha_os.product.us_forward_return_validation import format_us_forward_return_markdown

    md = format_us_forward_return_markdown(
        {
            "rows_matched": 3,
            "rows_considered": 10,
            "rows_skipped": 7,
            "horizons": [5, 20],
            "sample_quality": {
                "status": "thin",
                "reason": "thin",
                "matched_rows": 3,
                "interpretation": "x",
                "needed_more_samples": 7,
                "skip_pattern": "mixed",
            },
            "stale_skip_by_symbol": [{"symbol": "GLDM", "count": 4}],
            "skipped_reasons": {},
        }
    )
    assert "stale_skip_symbols" in md
    assert "GLDM(4)" in md


def test_sample_quality_thin_includes_needed_more(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    sq = report["sample_quality"]
    assert sq["status"] == "thin"
    assert sq["needed_more_samples"] == 9
    assert sq["p3_progress"]["samples_needed_for_usable"] == 9
    assert "1/10" in sq["p3_progress"]["progress_label"]
    assert sq["next_commands"]


def test_veto_joined_when_note_has_veto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    cache_dir = tmp_path / "us_daily_bars"
    cache_dir.mkdir(parents=True)
    outputs = tmp_path / "outputs"
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        source="local_fixture",
        fetched_at="2026-05-23T12:00:00+00:00",
    )
    (cache_dir / "MSFT.json").write_text(
        usc.us_daily_bars_cache_path("MSFT").read_text(encoding="utf-8"), encoding="utf-8"
    )
    note = (
        "us_cache_signal observation_only status=ok momentum_label=uptrend "
        "veto_triggered=true veto_rules=rapid_mover not buy/sell advice"
    )
    obs_path.write_text(
        json.dumps(
            {
                "id": "v1",
                "created_at": f"{event_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": note,
                "evidence_ids": [],
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    assert report["veto_at_t"]["status"] == "joined"
    assert report["by_veto_status"].get("triggered", {}).get("count") == 1


def test_veto_legacy_rows_not_in_log(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    assert report["veto_at_t"]["status"] == "not_in_observation_log"


def test_markdown_includes_veto_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    cache_dir = tmp_path / "us_daily_bars"
    outputs = tmp_path / "outputs"
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache("MSFT", [dict(b) for b in bars], source="local_fixture")
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "MSFT.json").write_text(
        usc.us_daily_bars_cache_path("MSFT").read_text(encoding="utf-8"), encoding="utf-8"
    )
    obs_path.write_text(
        json.dumps(
            {
                "id": "v1",
                "created_at": f"{event_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": (
                    "us_cache_signal observation_only status=ok "
                    "veto_triggered=false not buy/sell advice"
                ),
                "evidence_ids": [],
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    md = format_us_forward_return_markdown(report)
    assert "## Veto-at-t" in md
    assert "joined" in md


def test_forward_markdown_includes_skip_pattern() -> None:
    report = {
        "sample_quality": {
            "status": "empty",
            "reason": "too recent",
            "interpretation": "wait",
            "skip_pattern": "fresh_log",
            "matched_rows": 0,
            "next_commands": [],
        },
        "rows_matched": 0,
        "rows_considered": 16,
        "rows_skipped": 16,
        "horizons": [5],
        "skipped_reasons": {"insufficient_future_bars": 16},
        "quality_buckets": {"global": {}},
    }
    md = format_us_forward_return_markdown(report)
    assert "skip_pattern: fresh_log" in md


def test_cli_invalid_horizons_exit_2() -> None:
    result = CliRunner().invoke(
        app,
        ["validate", "us-forward-returns", "--horizons", "0", "--format", "json"],
    )
    assert result.exit_code == 2
    assert "positive" in (result.stderr or result.stdout).lower()


def test_p3_stall_diagnosis_thin_fixed_at_one_match(obs_and_cache: tuple[Path, Path]) -> None:
    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        compute_us_forward_p3_stall_diagnosis,
    )

    obs_path, cache_dir = obs_and_cache
    stall = compute_us_forward_p3_stall_diagnosis(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(5, 20)
    )
    assert stall["matched_normal"] == 1
    assert stall["samples_needed_for_usable"] == 9
    assert stall["why_matched_stuck"]["normal_matched"] == 1
    assert "matchable_now" in stall["p3_bucket_counts"]


def test_p3_stall_insufficient_future_classification(
    tmp_path: Path, obs_and_cache: tuple[Path, Path]
) -> None:
    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        CATEGORY_INSUFFICIENT_FUTURE,
        compute_us_forward_p3_stall_diagnosis,
    )

    obs_path, cache_dir = obs_and_cache
    bars = load_bars_json_file(FIX_MSFT)
    last_date = bars[-1]["date"][:10]
    obs_path.write_text(
        obs_path.read_text(encoding="utf-8").strip()
        + "\n"
        + json.dumps(
            {
                "id": "fresh",
                "created_at": f"{last_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": (
                    "us_cache_signal observation_only status=ok momentum_label=uptrend "
                    "not buy/sell advice"
                ),
                "evidence_ids": [],
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stall = compute_us_forward_p3_stall_diagnosis(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(60,)
    )
    assert stall["user_category_counts"].get(CATEGORY_INSUFFICIENT_FUTURE, 0) >= 1
    assert stall["p3_bucket_counts"].get("will_be_matchable_after_date", 0) >= 1


def test_p3_stall_duplicate_same_week(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        CATEGORY_DUPLICATE_WEEK,
        compute_us_forward_p3_stall_diagnosis,
    )

    cache_dir = tmp_path / "us_daily_bars"
    outputs = tmp_path / "outputs"
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache("MSFT", [dict(b) for b in bars], source="local_fixture")
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "MSFT.json").write_text(
        usc.us_daily_bars_cache_path("MSFT").read_text(encoding="utf-8"), encoding="utf-8"
    )
    note = "us_cache_signal observation_only status=ok momentum_label=neutral not buy/sell advice"
    line = {
        "id": "a",
        "created_at": f"{event_date}T09:00:00+00:00",
        "symbol": "MSFT",
        "note": note,
        "evidence_ids": [],
        "tags": [],
    }
    line2 = {**line, "id": "b", "created_at": f"{event_date}T10:00:00+00:00"}
    obs_path.write_text(
        json.dumps(line) + "\n" + json.dumps(line2) + "\n", encoding="utf-8"
    )
    stall = compute_us_forward_p3_stall_diagnosis(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(5, 20)
    )
    assert stall["user_category_counts"].get(CATEGORY_DUPLICATE_WEEK, 0) >= 1
    assert stall["p3_bucket_counts"].get("dead_rows_or_duplicate_rows", 0) >= 1


def test_backtest_high_normal_milestone_thin(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(5, 20)
    )
    stall = report.get("p3_stall_diagnosis") or {}
    assert report["sample_quality"]["status"] == "thin"
    assert report["rows_matched"] == 1
    why = stall.get("why_matched_stuck") or {}
    assert why.get("normal_matched") == 1
    assert int(why.get("backtest_within_cache_matched") or 0) >= 1
    assert "backtest" in (why.get("gap_explained_by") or "").lower()


def test_markdown_includes_p3_stall_and_next_actions(obs_and_cache: tuple[Path, Path]) -> None:
    obs_path, cache_dir = obs_and_cache
    report = compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir)
    md = format_us_forward_return_markdown(report)
    assert "## P3 stall diagnosis" in md
    assert "matchable_now" in md
    assert "Next actions" in md
    assert "normal matched" in md.lower() or "normal_matched" in md


def test_dedupe_counterfactual_suppresses_duplicate_week(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.data.us_daily_bars_cache as usc

    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        compute_us_forward_p3_stall_diagnosis,
    )

    cache_dir = tmp_path / "us_daily_bars"
    outputs = tmp_path / "outputs"
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    event_date = bars[-21]["date"][:10]
    usc.save_us_daily_bars_cache("MSFT", [dict(b) for b in bars], source="local_fixture")
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "MSFT.json").write_text(
        usc.us_daily_bars_cache_path("MSFT").read_text(encoding="utf-8"), encoding="utf-8"
    )
    note = "us_cache_signal observation_only status=ok momentum_label=neutral not buy/sell advice"
    line = {
        "id": "a",
        "created_at": f"{event_date}T09:00:00+00:00",
        "symbol": "MSFT",
        "note": note,
        "evidence_ids": [],
        "tags": [],
    }
    obs_path.write_text(
        json.dumps(line) + "\n" + json.dumps({**line, "id": "b"}) + "\n",
        encoding="utf-8",
    )
    stall = compute_us_forward_p3_stall_diagnosis(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(5, 20)
    )
    dc = stall.get("dedupe_counterfactual") or {}
    assert dc.get("duplicate_rows_suppressed") == 1
    assert dc.get("unique_symbol_weeks") == 1
    assert dc.get("multi_log_week_groups") == 1


def test_horizon_maturity_estimate_sessions(obs_and_cache: tuple[Path, Path]) -> None:
    from invis_alpha_os.product.us_forward_p3_stall_diagnosis import (
        compute_us_forward_p3_stall_diagnosis,
    )

    obs_path, cache_dir = obs_and_cache
    bars = load_bars_json_file(FIX_MSFT)
    last_date = bars[-1]["date"][:10]
    obs_path.write_text(
        obs_path.read_text(encoding="utf-8").strip()
        + "\n"
        + json.dumps(
            {
                "id": "tail",
                "created_at": f"{last_date}T09:00:00+00:00",
                "symbol": "MSFT",
                "note": (
                    "us_cache_signal observation_only status=ok momentum_label=uptrend "
                    "not buy/sell advice"
                ),
                "evidence_ids": [],
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stall = compute_us_forward_p3_stall_diagnosis(
        observation_path=obs_path, cache_dir=cache_dir, horizons=(60,)
    )
    hm = stall.get("horizon_maturity") or {}
    assert "sessions_until_histogram" in hm
    assert "l1_gate" in hm
    assert hm["l1_gate"]["frequency"] == "monthly 1-2 times"
    md = format_us_forward_return_markdown(
        compute_us_forward_returns(observation_path=obs_path, cache_dir=cache_dir, horizons=(60,))
    )
    assert "### Horizon maturity estimate" in md
    assert "### Dedupe counterfactual" in md


def test_resolution_breakdown_embeds_stall_diagnosis(obs_and_cache: tuple[Path, Path]) -> None:
    from invis_alpha_os.product.us_forward_return_validation import (
        compute_us_forward_resolution_breakdown,
    )

    obs_path, cache_dir = obs_and_cache
    bd = compute_us_forward_resolution_breakdown(
        observation_path=obs_path, cache_dir=cache_dir
    )
    stall = bd.get("p3_stall_diagnosis") or {}
    assert stall.get("p3_bucket_counts")
    assert stall.get("user_category_counts")
