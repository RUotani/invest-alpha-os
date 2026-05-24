"""Forward event date resolution (cache-only)."""

from __future__ import annotations

from datetime import date

from invis_alpha_os.observation.us_signal_note import (
    build_us_signal_observation_note,
    parse_us_signal_observation_note,
)
from invis_alpha_os.product.forward_event_resolution import (
    resolve_forward_horizons,
    resolve_observation_event_date,
)
from invis_alpha_os.product.us_forward_return_validation import compute_us_forward_returns
from invis_alpha_os.signals.momentum import DailyBar


def _bars(closes: list[float], start: str = "2026-01-01") -> list[DailyBar]:
    y, m, d = int(start[0:4]), int(start[5:7]), int(start[8:10])
    out: list[DailyBar] = []
    for i, c in enumerate(closes):
        day = d + i
        month, year = m, y
        while day > 28:
            day -= 28
            month += 1
            if month > 12:
                month = 1
                year += 1
        out.append(
            {
                "date": f"{year:04d}-{month:02d}-{day:02d}",
                "open": c,
                "high": c,
                "low": c,
                "close": c,
                "volume": 1.0,
            }
        )
    return out


def test_build_us_signal_note_includes_as_of() -> None:
    note = build_us_signal_observation_note(
        {"status": "ok", "momentum_label": "uptrend", "last_date": "2024-04-10"}
    )
    assert "as_of=2024-04-10" in note
    parsed = parse_us_signal_observation_note(note)
    assert parsed.get("as_of") == "2024-04-10"


def test_resolve_observation_event_date_prefers_as_of() -> None:
    note = build_us_signal_observation_note({"status": "ok", "last_date": "2024-04-10"})
    event, source = resolve_observation_event_date(
        note=note,
        created_at="2026-05-24T09:00:00+00:00",
    )
    assert event == date(2024, 4, 10)
    assert source == "as_of"


def test_backtest_within_cache_enables_forward(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import json
    from pathlib import Path

    import invis_alpha_os.data.us_daily_bars_cache as usc

    outputs = tmp_path / "outputs"
    cache_dir = outputs / "us_daily_bars"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)

    bars = _bars([100 + i * 0.5 for i in range(72)])
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-24T12:00:00+00:00",
        generated_at="2026-05-24T12:00:05+00:00",
    )
    saved = usc.us_daily_bars_cache_path("MSFT")
    (cache_dir / "MSFT.json").write_text(saved.read_text(encoding="utf-8"), encoding="utf-8")

    note = build_us_signal_observation_note({"status": "ok", "momentum_label": "uptrend"})
    obs_path = outputs / "observation_log" / "observation_log.jsonl"
    obs_path.parent.mkdir(parents=True)
    obs_path.write_text(
        json.dumps(
            {
                "id": "1",
                "created_at": "2026-05-24T09:00:00+00:00",
                "symbol": "MSFT",
                "note": note,
                "evidence_ids": [],
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    without = compute_us_forward_returns(
        observation_path=obs_path,
        cache_dir=cache_dir,
        horizons=(5, 20, 60),
    )
    assert without["rows_matched"] == 0
    assert without["skipped_reasons"].get("cache_stale_event_after_cache_end") == 1

    with_backtest = compute_us_forward_returns(
        observation_path=obs_path,
        cache_dir=cache_dir,
        horizons=(5, 20, 60),
        backtest_within_cache=True,
    )
    assert with_backtest["rows_matched"] == 1
    assert with_backtest["examples"][0].get("event_resolution") == "backtest_within_cache"


def test_resolve_forward_horizons_short_horizon_only() -> None:
    bars = _bars([100 + i for i in range(30)])
    event = date(2026, 1, 25)
    resolved = resolve_forward_horizons(bars, event, (5, 20), backtest_within_cache=False)
    assert resolved is not None
    idx, returns, _tag = resolved
    assert returns["5"] is not None
