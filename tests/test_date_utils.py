"""JST date helpers (Hotfix A)."""

from datetime import datetime, timezone

import pytest

from invis_alpha_os.utils.date_utils import date_jst_iso, today_jst_iso


def test_utc_2026_05_11_1530_maps_to_jst_2026_05_12():
    utc = datetime(2026, 5, 11, 15, 30, tzinfo=timezone.utc)
    assert date_jst_iso(utc) == "2026-05-12"


def test_utc_2026_05_11_1459_maps_to_jst_2026_05_11():
    utc = datetime(2026, 5, 11, 14, 59, tzinfo=timezone.utc)
    assert date_jst_iso(utc) == "2026-05-11"


def test_date_jst_iso_rejects_naive_datetime():
    with pytest.raises(ValueError, match="timezone-aware"):
        date_jst_iso(datetime(2026, 5, 11, 12, 0))


def test_today_jst_iso_is_callable_smoke():
    s = today_jst_iso()
    assert len(s) == 10
    assert s[4] == "-" and s[7] == "-"
