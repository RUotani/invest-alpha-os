"""Tests for US signal ISO week dedupe helpers (P3 forward)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


from invis_alpha_os.observation.service import ObservationService
from invis_alpha_os.observation.us_signals_batch import (
    log_us_signals_batch_observations,
    observation_batch_failed,
)
from invis_alpha_os.product.us_signal_iso_week_dedupe import (
    build_p3_weekly_write_plan,
    estimate_p3_iso_week_rollover,
    evaluate_p3_l1_write_gate,
    iso_week_key,
    load_existing_symbol_iso_week_keys,
    next_iso_week_start,
)

REPO = Path(__file__).resolve().parents[1]
FIX_MANIFEST = REPO / "tests" / "fixtures" / "us_equities" / "us_cache_signals_batch_minimal.json"


def test_skip_duplicate_iso_week_on_second_batch(tmp_path: Path) -> None:
    obs_path = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs_path, outcome_path=tmp_path / "out.jsonl")
    first = log_us_signals_batch_observations(FIX_MANIFEST, path_base=REPO, service=svc)
    assert first["logged"] == 2
    second = log_us_signals_batch_observations(
        FIX_MANIFEST,
        path_base=REPO,
        service=svc,
        skip_duplicate_iso_week=True,
    )
    assert second["logged"] == 0
    assert second["skipped_duplicate_iso_week"] == 2
    assert not observation_batch_failed(second)
    assert len(obs_path.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_skip_duplicate_iso_week_default_logs_all(tmp_path: Path) -> None:
    obs_path = tmp_path / "observation_log.jsonl"
    svc = ObservationService(observation_path=obs_path, outcome_path=tmp_path / "out.jsonl")
    log_us_signals_batch_observations(FIX_MANIFEST, path_base=REPO, service=svc)
    second = log_us_signals_batch_observations(FIX_MANIFEST, path_base=REPO, service=svc)
    assert second["logged"] == 2
    assert second.get("skipped_duplicate_iso_week", 0) == 0


def test_build_p3_weekly_write_plan_splits(tmp_path: Path) -> None:
    obs_path = tmp_path / "observation_log.jsonl"
    note = "us_cache_signal observation_only status=ok momentum_label=neutral as_of=2024-04-10 not buy/sell advice"
    line = {
        "id": "a",
        "created_at": "2024-04-10T09:00:00+00:00",
        "symbol": "MSFT",
        "note": note,
        "evidence_ids": [],
        "tags": [],
    }
    obs_path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    plan = build_p3_weekly_write_plan(
        observation_path=obs_path,
        planned_writes=[
            {"symbol": "MSFT", "last_date": "2024-04-10"},
            {"symbol": "NVDA", "last_date": "2024-04-12"},
        ],
    )
    assert plan["skip_duplicate_count"] == 1
    assert plan["write_now_count"] == 1
    assert plan["write_now"][0]["symbol"] == "NVDA"


def test_load_existing_symbol_iso_week_keys_empty(tmp_path: Path) -> None:
    assert load_existing_symbol_iso_week_keys(tmp_path / "missing.jsonl") == set()


def test_evaluate_p3_l1_write_gate_ready() -> None:
    gate = evaluate_p3_l1_write_gate(
        write_now_count=3,
        skip_duplicate_count=5,
        will_be_matchable_after_date_rows=2,
    )
    assert gate["status"] == "ready"
    assert gate["l1_recommended"] is True


def test_evaluate_p3_l1_write_gate_blocked_duplicate() -> None:
    gate = evaluate_p3_l1_write_gate(
        write_now_count=0,
        skip_duplicate_count=16,
        will_be_matchable_after_date_rows=8,
    )
    assert gate["status"] == "blocked_duplicate_iso_week"
    assert gate["l1_recommended"] is False
    assert "will_be_matchable_after_date" in gate["next_action"]


def test_next_iso_week_start() -> None:
    # 2024-04-10 is Wednesday ISO week 15
    nxt = next_iso_week_start(date(2024, 4, 10))
    assert nxt.isoformat() == "2024-04-15"
    assert iso_week_key(nxt) != iso_week_key(date(2024, 4, 10))


def test_estimate_p3_iso_week_rollover() -> None:
    rollover = estimate_p3_iso_week_rollover(
        skip_duplicate=[{"symbol": "MSFT", "last_date": "2024-04-10"}],
        reference_date=date(2024, 4, 10),
    )
    assert rollover["status"] == "waiting_for_iso_week_rollover"
    assert rollover["earliest_next_iso_week_start"] == "2024-04-15"
    assert rollover["days_until_earliest_rollover"] == 5
    assert rollover["projected_write_now_symbols_at_rollover"] == 1
    assert rollover["rollover_passed"] is False


def test_estimate_p3_iso_week_rollover_passed_write_still_blocked() -> None:
    rollover = estimate_p3_iso_week_rollover(
        skip_duplicate=[{"symbol": "MSFT", "last_date": "2024-04-10"}],
        reference_date=date(2024, 4, 20),
    )
    assert rollover["status"] == "rollover_passed_write_still_blocked"
    assert rollover["days_until_earliest_rollover"] == 0
    assert rollover["rollover_passed"] is True
    assert "rollover date has passed" in rollover["l1_unblock_hint"]
    assert "cache/as_of has not advanced" in rollover["l1_unblock_hint"]
    assert "0 =" in rollover["days_until_earliest_rollover_note"]


def test_evaluate_p3_l1_write_gate_rollover_passed_wording() -> None:
    rollover = estimate_p3_iso_week_rollover(
        skip_duplicate=[{"symbol": "MSFT", "last_date": "2024-04-10"}],
        reference_date=date(2024, 4, 20),
    )
    gate = evaluate_p3_l1_write_gate(
        write_now_count=0,
        skip_duplicate_count=16,
        will_be_matchable_after_date_rows=8,
        iso_week_rollover=rollover,
    )
    assert gate["status"] == "blocked_duplicate_iso_week"
    assert "rollover date has passed" in gate["next_action"]
    assert "wait for ISO week rollover" not in gate["next_action"]


def test_build_p3_weekly_write_plan_rollover_passed(tmp_path: Path) -> None:
    obs_path = tmp_path / "observation_log.jsonl"
    note = "us_cache_signal observation_only status=ok momentum_label=neutral as_of=2024-04-10 not buy/sell advice"
    line = {
        "id": "a",
        "created_at": "2024-04-10T09:00:00+00:00",
        "symbol": "MSFT",
        "note": note,
        "evidence_ids": [],
        "tags": [],
    }
    obs_path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    plan = build_p3_weekly_write_plan(
        observation_path=obs_path,
        planned_writes=[{"symbol": "MSFT", "last_date": "2024-04-10"}],
        will_be_matchable_after_date_rows=8,
    )
    rollover = plan["iso_week_rollover"]
    rollover["reference_date"] = "2024-04-20"
    rollover = estimate_p3_iso_week_rollover(
        skip_duplicate=plan["skip_duplicate"],
        reference_date=date(2024, 4, 20),
    )
    gate = evaluate_p3_l1_write_gate(
        write_now_count=plan["write_now_count"],
        skip_duplicate_count=plan["skip_duplicate_count"],
        will_be_matchable_after_date_rows=8,
        iso_week_rollover=rollover,
    )
    assert plan["write_now_count"] == 0
    assert gate["next_action"]
    assert "rollover date has passed" in gate["next_action"]
