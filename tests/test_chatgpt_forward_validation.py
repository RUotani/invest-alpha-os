from __future__ import annotations

import json
from pathlib import Path

from invis_alpha_os.reports.chatgpt_forward_validation import build_validation_seed, evaluate_validation_seeds


def test_build_validation_seed() -> None:
    payload = {"candidates": [{"ticker": "285A", "market": "JP", "classification": "top_pick", "latest_close": 100.0}]}
    seed = build_validation_seed(report_date="2026-05-27", context_json_payload=payload)
    assert seed.json_payload["evaluation_dates"]["plus_4w"] == "2026-06-24"
    assert seed.json_payload["candidates"][0]["ticker"] == "285A"


def test_evaluate_validation_seeds_without_cache(tmp_path: Path) -> None:
    seeds_dir = tmp_path / "seeds" / "2026" / "2026-05-27"
    seeds_dir.mkdir(parents=True)
    seed_payload = {
        "report_date": "2026-05-27",
        "evaluation_dates": {"plus_4w": "2026-06-24", "plus_12w": "2026-08-19", "plus_26w": "2026-11-25"},
        "candidates": [{"ticker": "NOFILE", "market": "US", "latest_close_at_report": 100.0, "future_evaluation_dates": {"plus_4w": "2026-06-24", "plus_12w": "2026-08-19", "plus_26w": "2026-11-25"}}],
    }
    (seeds_dir / "decision_seed.json").write_text(json.dumps(seed_payload), encoding="utf-8")
    out = evaluate_validation_seeds(as_of_date="2026-12-01", seeds_dir=tmp_path / "seeds", out_dir=tmp_path)
    assert out["result_4w"].is_file()
    data = json.loads(out["result_4w"].read_text(encoding="utf-8"))
    assert data["horizon"] == "4w"
    assert out["dashboard_md"].is_file()
    assert out["dashboard_json"].is_file()
