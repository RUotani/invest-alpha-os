from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.jp_alternative_provider_readiness import build_jp_alternative_provider_readiness


def test_build_jp_alternative_provider_readiness_lists_manual_csv_first(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "20260306")
    repo_root = Path(__file__).resolve().parents[1]
    result = build_jp_alternative_provider_readiness(
        report_date="2026-05-27",
        targets_csv="5802,6645,5801,285A,5803",
        repo_root=repo_root,
    )
    assert result.json_payload["recommended_provider"] == "manual_csv"
    providers = [row["provider"] for row in result.json_payload["alternative_candidates"]]
    assert providers[0] == "manual_csv"
    assert "jquants" in providers
    assert "scraping" in providers
    assert result.json_payload["alternative_candidates"][-1]["available"] is False
    assert "JP Alternative Provider Readiness" in result.markdown_text


def test_jp_alternative_readiness_contract_limited_when_cache_at_contract_end(monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "20260306")
    repo_root = Path(__file__).resolve().parents[1]

    def _mock_load(ticker: str):
        if ticker != "5802":
            return None
        return ([{"date": "2026-03-06", "close": 100.0}], {"source": "test"})

    monkeypatch.setattr(
        "invis_alpha_os.reports.jp_alternative_provider_readiness.load_jquants_daily_bars_cache",
        _mock_load,
    )
    result = build_jp_alternative_provider_readiness(
        report_date="2026-05-27",
        targets_csv="5802",
        repo_root=repo_root,
    )
    assert result.json_payload["jquants_contract_limited"] is True
