from __future__ import annotations

from invis_alpha_os.config.env_bool import (
    general_env_truthy,
    provider_allow_flag_truthy,
    strict_confirm_flag_truthy,
)


def test_provider_allow_flag_truthy_accepts_common_values() -> None:
    for value in ("true", "1", "yes", "y", "on", "YES", "TRUE"):
        assert provider_allow_flag_truthy(value) is True


def test_provider_allow_flag_truthy_rejects_falsey_values() -> None:
    for value in ("false", "0", "no", "n", "off", "", None):
        assert provider_allow_flag_truthy(value) is False


def test_strict_confirm_flag_requires_exact_yes() -> None:
    assert strict_confirm_flag_truthy("YES") is True
    assert strict_confirm_flag_truthy("yes") is False
    assert strict_confirm_flag_truthy("true") is False


def test_general_env_truthy() -> None:
    assert general_env_truthy("true") is True
    assert general_env_truthy("1") is True
    assert general_env_truthy("yes") is True
    assert general_env_truthy("on") is False
