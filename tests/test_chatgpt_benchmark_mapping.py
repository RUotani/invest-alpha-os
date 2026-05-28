from __future__ import annotations

from invis_alpha_os.reports.chatgpt_benchmark_mapping import infer_benchmark_for_candidate


def test_infer_benchmark_for_us() -> None:
    assert infer_benchmark_for_candidate(market="US", ticker="AAPL") == "SPY"


def test_infer_benchmark_for_jp() -> None:
    assert infer_benchmark_for_candidate(market="JP", ticker="285A") == "TOPIX"

