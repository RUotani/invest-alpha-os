from __future__ import annotations

from invis_alpha_os.reports.contract_env_status import (
    append_contract_env_warning,
    build_contract_env_status,
    jp_stale_candidates_without_contract_env,
    jquants_contract_env_loaded,
)


def test_jquants_contract_env_loaded_when_data_available_to_present(monkeypatch) -> None:
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "20260306")
    assert jquants_contract_env_loaded() is True
    status = build_contract_env_status()
    assert status["contract_env_not_loaded"] is False


def test_contract_env_not_loaded_without_data_available_to(monkeypatch) -> None:
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)
    assert jquants_contract_env_loaded() is False
    status = build_contract_env_status()
    assert status["contract_env_not_loaded"] is True
    assert status["contract_env_hint"] is not None


def test_append_contract_env_warning_for_jp_stale(monkeypatch) -> None:
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)
    warnings = append_contract_env_warning(
        ["data_update_required"],
        market="JP",
        freshness_classification="data_update_required",
    )
    assert "contract_env_not_loaded" in warnings


def test_append_contract_env_warning_skips_us(monkeypatch) -> None:
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)
    warnings = append_contract_env_warning(
        ["stale"],
        market="US",
        freshness_classification="stale",
    )
    assert "contract_env_not_loaded" not in warnings


def test_jp_stale_candidates_without_contract_env_lists_tickers(monkeypatch) -> None:
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)
    tickers = jp_stale_candidates_without_contract_env(
        [
            {"ticker": "5802", "market": "JP", "freshness_classification": "data_update_required"},
            {"ticker": "QQQ", "market": "ETF", "freshness_classification": "stale"},
        ]
    )
    assert tickers == ["5802"]
