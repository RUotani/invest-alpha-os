from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.reports import manual_csv_discovery as discovery_mod
from invis_alpha_os.reports.manual_csv_discovery import build_manual_csv_discovery


@pytest.fixture
def discovery_root(tmp_path: Path) -> Path:
    csv_path = tmp_path / "manual_jp_bars.csv"
    csv_path.write_text(
        "ticker,date,open,high,low,close,volume\n"
        "5802,2026-05-27,100,110,90,105,1000\n",
        encoding="utf-8",
    )
    return tmp_path


def test_discovery_finds_safe_candidate(
    discovery_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(discovery_mod, "_search_roots", lambda: [discovery_root])
    result = build_manual_csv_discovery(report_date="2026-05-27", repo_root=tmp_path)
    assert result.json_payload["csv_candidates_found"] == 1
    assert result.json_payload["safe_to_validate"] is True
    assert result.selected_path is not None
    assert result.selected_path.name == "manual_jp_bars.csv"
    assert "resolved_path" not in result.json_payload.get("selected_candidate", {})
