from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.reports import manual_data_discovery as data_disc_mod
from invis_alpha_os.reports.manual_data_discovery import build_manual_data_discovery


@pytest.fixture
def discovery_root(tmp_path: Path) -> Path:
    (tmp_path / "manual_jp_bars.tsv").write_text(
        "ticker\tdate\topen\thigh\tlow\tclose\tvolume\n"
        "5802\t2026-05-27\t100\t110\t90\t105\t1000\n",
        encoding="utf-8",
    )
    return tmp_path


def test_data_discovery_finds_tsv(
    discovery_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(data_disc_mod, "_search_roots", lambda: [discovery_root])
    result = build_manual_data_discovery(report_date="2026-05-27", repo_root=tmp_path)
    assert result.json_payload["candidates_found"] == 1
    assert result.json_payload["searched_location_count"] == 1
    assert result.json_payload["contents_printed"] is False
    assert result.json_payload["safe_to_parse"] is True
    assert result.selected_path is not None
    assert result.selected_path.suffix == ".tsv"
