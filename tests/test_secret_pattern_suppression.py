from __future__ import annotations

from invis_alpha_os.security.secret_pattern_suppression import (
    evaluate_secret_hit,
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
    suppress, _, category = evaluate_secret_hit(
        rel_path="docs/setup.md",
        pattern_label="jquants_key",
        sample_text=sample,
    )
    assert suppress
    assert category == "documentation_reference"


def test_suppress_scripts_clearing_env() -> None:
    sample = "export JQUANTS_API_KEY= JQUANTS_ENABLED=\n"
    suppress, reason, category = evaluate_secret_hit(
        rel_path="scripts/run_weekly_candidate_brief.sh",
        pattern_label="jquants_key",
        sample_text=sample,
    )
    assert suppress
    assert category == "tooling_pattern_reference"


def test_suppress_tests_gmail_fixture_reference() -> None:
    sample = 'cred.write_text(\'{"installed": {"client_secret": "y"}}\', encoding="utf-8")\n'
    suppress, _, category = evaluate_secret_hit(
        rel_path="tests/test_daily_email_delivery.py",
        pattern_label="gmail_token",
        sample_text=sample,
    )
    assert suppress
    assert category == "test_fixture"


def test_suppress_src_cli_env_help_reference() -> None:
    sample = 'help="Optional test recipient override (default: GMAIL_TO env).",\n'
    suppress, _, category = evaluate_secret_hit(
        rel_path="src/invis_alpha_os/cli/main.py",
        pattern_label="gmail_token",
        sample_text=sample,
    )
    assert suppress
    assert category == "documentation_reference"


def test_do_not_suppress_realistic_assignment_in_docs() -> None:
    sample = "JQUANTS_API_KEY=" + ("a" * 32) + "\n"
    suppress, _, category = evaluate_secret_hit(
        rel_path="docs/setup.md",
        pattern_label="jquants_key",
        sample_text=sample,
    )
    assert not suppress
    assert category == "real_secret_risk"


def test_should_suppress_legacy_docs_helper() -> None:
    assert should_suppress_secret_hit(
        rel_path="docs/setup.md",
        pattern_label="jquants_key",
        sample_text="JQUANTS_API_KEY=placeholder\n",
    )
