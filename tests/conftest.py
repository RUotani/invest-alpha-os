"""Pytest defaults: isolate J-Quants data-availability env unless a test sets it."""

import pytest


@pytest.fixture(autouse=True)
def _clear_jquants_data_availability_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 5.6: tests opt in via monkeypatch.setenv; shell exports must not break CI."""

    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_FROM", raising=False)
    monkeypatch.delenv("JQUANTS_DATA_AVAILABLE_TO", raising=False)
