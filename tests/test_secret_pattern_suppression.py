from __future__ import annotations

from invis_alpha_os.security.secret_pattern_suppression import (
    should_suppress_secret_hit,
    value_looks_like_placeholder,
    value_looks_like_real_secret,
)


def test_placeholder_values_detected() -> None:
    assert value_looks_like_placeholder("YOUR_API_KEY")
    assert value_looks_like_placeholder("changeme")
    assert not value_looks_like_real_secret("changeme")


def test_realistic_secret_not_placeholder() -> None:
    token = "a" * 32
    assert value_looks_like_real_secret(token)
    assert not value_looks_like_placeholder(token)


def test_suppress_docs_placeholder_api_key() -> None:
    sample = "JQUANTS_API_KEY=your_api_key_here\n"
    assert should_suppress_secret_hit(
        rel_path="docs/setup.md",
        pattern_label="jquants_key",
        sample_text=sample,
    )


def test_do_not_suppress_realistic_assignment_in_docs() -> None:
    sample = "JQUANTS_API_KEY=" + ("a" * 32) + "\n"
    assert not should_suppress_secret_hit(
        rel_path="docs/setup.md",
        pattern_label="jquants_key",
        sample_text=sample,
    )
