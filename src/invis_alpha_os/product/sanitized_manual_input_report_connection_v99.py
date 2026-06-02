"""v99 sanitized/manual input report connection helpers."""

from __future__ import annotations

from invis_alpha_os.product.sanitized_manual_input_v98 import (
    build_redacted_sanitized_manual_input_fixture_v98,
    validate_sanitized_manual_input_v98,
    validate_v95_parity_from_sanitized_manual_input_v98,
)


def build_sanitized_manual_input_summary_lines_v99() -> tuple[str, ...]:
    fixture = build_redacted_sanitized_manual_input_fixture_v98()
    result = validate_sanitized_manual_input_v98(fixture, current_month=fixture.as_of_month)
    parity = validate_v95_parity_from_sanitized_manual_input_v98(fixture)
    return (
        (
            f"Sanitized Input: 判定 {result.overall_severity.value.upper()} / "
            f"{fixture.as_of_month} / {fixture.currency} / {fixture.amount_unit}"
        ),
        (
            f"Sanitized Guardrail: 現金{fixture.assets[0].ratio_pct:.1f}%はminimum "
            f"{fixture.cash_minimum_guardrail_pct:.1f}%未満 / "
            f"個別株{fixture.assets[2].ratio_pct:.1f}%はtarget "
            f"{fixture.single_stock_target_min_pct:.1f}〜{fixture.single_stock_target_max_pct:.1f}%超過"
        ),
        f"Sanitized Parity: v97/v95整合 {parity.overall_severity.value.upper()}",
    )
