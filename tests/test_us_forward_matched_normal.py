"""Tests for P3 matched_normal vs rows_matched resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.product.forward_p3_status import (
    build_forward_p3_status_bundle,
    format_forward_p3_status_markdown,
)
from invis_alpha_os.product.us_forward_return_validation import (
    forward_p3_sample_quality_status,
    us_forward_matched_normal_for_p3,
    us_forward_p3_axis,
)
from invis_alpha_os.signals.momentum import load_bars_json_file

REPO = Path(__file__).resolve().parents[1]
FIX_MSFT = REPO / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


def test_matched_normal_prefers_stall_over_rows_matched() -> None:
    assert (
        us_forward_matched_normal_for_p3(
            rows_matched=20,
            stall_diagnosis={"matched_normal": 1},
        )
        == 1
    )


def test_matched_normal_prefers_summary_over_stall() -> None:
    assert (
        us_forward_matched_normal_for_p3(
            rows_matched=20,
            stall_diagnosis={"matched_normal": 2},
            p3_summary={"matched_normal": 1},
        )
        == 1
    )


def test_matched_normal_falls_back_to_rows_matched() -> None:
    assert us_forward_matched_normal_for_p3(rows_matched=7) == 7


def test_forward_p3_sample_quality_status() -> None:
    assert forward_p3_sample_quality_status(0) == "empty"
    assert forward_p3_sample_quality_status(1) == "thin"
    assert forward_p3_sample_quality_status(10) == "usable"


def test_us_forward_p3_axis_prefers_matched_normal_over_raw_usable() -> None:
    axis = us_forward_p3_axis(
        {
            "rows_matched": 20,
            "sample_quality": {
                "status": "usable",
                "p3_progress": {"progress_label": "usable (20 matched)"},
            },
            "p3_stall_diagnosis": {"matched_normal": 1},
        }
    )
    assert axis["rows_matched_all"] == 20
    assert axis["matched_normal"] == 1
    assert axis["all_rows_sample_quality_status"] == "usable"
    assert axis["p3_sample_quality_status"] == "thin"
    assert axis["samples_needed_for_usable"] == 9
    assert "1/10" in axis["p3_progress"]["progress_label"]


def test_forward_p3_status_raw_usable_p3_thin_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When raw rows_matched implies usable but matched_normal is thin, markdown must not imply P3 usable."""

    import invis_alpha_os.config.paths as config_paths
    import invis_alpha_os.data.us_daily_bars_cache as usc

    cache_dir = tmp_path / "us_daily_bars"
    outputs = tmp_path / "outputs"
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    monkeypatch.setattr(config_paths, "OUTPUTS_DIR", outputs)
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
    # 12 duplicate same-week rows → raw rows_matched=12 (usable) but matched_normal=1
    obs_path.write_text(
        "\n".join(json.dumps({**line, "id": f"dup{i}"}) for i in range(12)) + "\n",
        encoding="utf-8",
    )
    report = build_forward_p3_status_bundle(
        path_base=tmp_path,
        observation_path=obs_path,
        cache_dir=cache_dir,
    )
    us = report["us_forward"]
    assert us["rows_matched"] >= 10
    assert us["all_rows_sample_quality_status"] == "usable"
    assert us["matched_normal"] == 1
    assert us["p3_sample_quality_status"] == "thin"
    assert us["samples_needed_for_usable"] == 9
    assert "1/10" in (us["p3_progress"] or {}).get("progress_label", "")
    assert report["us_p3_usable"] is False
    md = format_forward_p3_status_markdown(report)
    assert "all_rows_sample_quality: usable" in md
    assert "p3_sample_quality: thin" in md
    assert "p3_progress: 1/10 toward usable" in md
    assert "samples_needed_for_usable: 9" in md
    assert "p3_sample_quality: usable" not in md
