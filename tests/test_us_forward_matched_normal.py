"""Tests for P3 matched_normal vs rows_matched resolution."""

from __future__ import annotations

from invis_alpha_os.product.us_forward_return_validation import us_forward_matched_normal_for_p3


def test_matched_normal_prefers_stall_over_rows_matched() -> None:
    assert (
        us_forward_matched_normal_for_p3(
            rows_matched=20,
            stall_diagnosis={"matched_normal": 1},
        )
        == 1
    )


def test_matched_normal_prefers_summary_over_stall() -> None:
    assert (
        us_forward_matched_normal_for_p3(
            rows_matched=20,
            stall_diagnosis={"matched_normal": 2},
            p3_summary={"matched_normal": 1},
        )
        == 1
    )


def test_matched_normal_falls_back_to_rows_matched() -> None:
    assert us_forward_matched_normal_for_p3(rows_matched=7) == 7
