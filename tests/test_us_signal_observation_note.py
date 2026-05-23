"""US signal observation note parse/build (shared parser)."""

from __future__ import annotations

from invis_alpha_os.observation.us_signal_note import (
    build_us_signal_observation_note,
    parse_us_signal_observation_note,
)


def test_parse_legacy_note_without_veto() -> None:
    note = (
        "us_cache_signal observation_only status=ok momentum_label=uptrend "
        "not buy/sell advice"
    )
    parsed = parse_us_signal_observation_note(note)
    assert parsed["status"] == "ok"
    assert parsed["momentum_label"] == "uptrend"
    assert "veto_triggered" not in parsed


def test_parse_note_with_veto() -> None:
    note = (
        "us_cache_signal observation_only status=ok momentum_label=uptrend "
        "veto_triggered=true veto_rules=rapid_mover,low_volume not buy/sell advice"
    )
    parsed = parse_us_signal_observation_note(note)
    assert parsed["veto_triggered"] is True
    assert parsed["veto_rules"] == ["rapid_mover", "low_volume"]


def test_malformed_veto_ignored() -> None:
    note = "us_cache_signal observation_only status=ok veto_triggered=maybe not buy/sell advice"
    parsed = parse_us_signal_observation_note(note)
    assert "veto_triggered" not in parsed


def test_build_roundtrip_veto_fields() -> None:
    preview = {"status": "ok", "momentum_label": "uptrend"}
    note = build_us_signal_observation_note(
        preview, veto_triggered=True, veto_rules=["rapid_mover"]
    )
    parsed = parse_us_signal_observation_note(note)
    assert parsed["veto_triggered"] is True
    assert parsed["veto_rules"] == ["rapid_mover"]
