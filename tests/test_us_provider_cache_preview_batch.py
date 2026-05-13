"""Main R5–R5.2: multi-symbol US Stooq cache preview aggregation (no HTTP in default tests)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.data import us_provider_cache_preview_batch as upcb
from invis_alpha_os.data import us_provider_live_preview as uplp

runner = CliRunner()


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(uplp.CONFIRM_US_LIVE_HTTP_ENV, raising=False)
    monkeypatch.delenv(uplp.CONFIRM_US_CACHE_WRITE_ENV, raising=False)


def test_batch_dry_run_two_symbols_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("batch dry-run must not open HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)
    out = upcb.run_stooq_cache_preview_batch(["MSFT", "GOOGL"], live=False, write_cache=False)
    assert out["status"] == "batch_preview_ok"
    assert out["live_http_requested"] is False
    assert out["write_cache_requested"] is False
    assert out["live_http_performed"] is False
    assert out["cache_write_performed"] is False
    assert out["raw_response_included"] is False
    assert out["observation_only"] is True
    assert len(out["results"]) == 2
    for row in out["results"]:
        assert row["status"] == "dry_run"
        assert row["reason"] is None
        assert row["body_kind"] is None
        assert row["raw_response_included"] is False
        assert row["cache_write_allowed"] is False
        assert row["cache_write_blocked_reason"] == "bulk_cache_writes_disabled_use_single_symbol_us_provider_cache_preview"
        assert "operator_next_action" in row
    assert out["summary"]["dry_run"] == 2
    osm = out["operator_summary"]
    assert osm["safe_dry_run_count"] == 2
    assert osm["invalid_symbol_count"] == 0


def test_batch_invalid_symbol_row_plus_valid() -> None:
    out = upcb.run_stooq_cache_preview_batch(["bogus/name", "QQQ"], live=False)
    assert out["status"] == "batch_preview_ok"
    assert len(out["results"]) == 2
    assert out["results"][0]["status"] == "validation_error"
    assert out["results"][0]["reason"] == "invalid_symbol"
    assert out["results"][1]["symbol"] == "QQQ"
    assert out["results"][1]["status"] == "dry_run"
    assert out["summary"]["validation_error"] == 1
    assert out["summary"]["dry_run"] == 1
    assert out["operator_summary"]["invalid_symbol_count"] == 1
    assert out["operator_summary"]["safe_dry_run_count"] == 1


def test_batch_rejects_write_cache_envelope() -> None:
    out = upcb.run_stooq_cache_preview_batch(["MSFT"], write_cache=True, live=False)
    assert out["status"] == "validation_error"
    assert out["reason"] == "batch_cache_write_not_supported"
    assert out["symbol_count"] == 0
    assert out["operator_summary"] == upcb.compute_operator_summary_from_rows([])


def test_batch_unsupported_provider() -> None:
    out = upcb.run_stooq_cache_preview_batch(["MSFT"], provider="alpha_vantage_preview")
    assert out["status"] == "validation_error"
    assert out["reason"] == "unsupported_provider"
    assert out["operator_summary"] == upcb.compute_operator_summary_from_rows([])


def test_batch_limit_trims_after_dedupe() -> None:
    out = upcb.run_stooq_cache_preview_batch(["MSFT", "AAPL", "MSFT"], limit=1, live=False)
    assert out["symbol_count"] == 1
    assert out["results"][0]["symbol"] == "MSFT"


def test_cli_batch_dry_watchlist_json_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("CLI dry batch must not HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview-batch",
            "--from-watchlist",
            "--provider",
            "stooq_preview",
            "--limit",
            "2",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    p = json.loads(r.stdout.strip())
    assert p["status"] == "batch_preview_ok"
    assert p["summary"]["dry_run"] == 2
    assert len(p["results"]) == 2
    assert p["operator_summary"]["safe_dry_run_count"] == 2


def test_batch_empty_inputs_validation() -> None:
    out = upcb.run_stooq_cache_preview_batch([], live=False)
    assert out["status"] == "validation_error"
    assert out["reason"] == "empty_symbol_batch"
    assert out["operator_summary"] == upcb.compute_operator_summary_from_rows([])


def test_operator_summary_buckets_via_mocked_live_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    seq: list[str] = []

    def _fake(norm: str, *, live: bool = False, write_cache: bool = False):  # noqa: ARG001
        seq.append(norm)
        if norm == "MSFT":
            return {
                "status": "parse_error",
                "reason": "stooq_vendor_no_data",
                "symbol": norm,
                "provider": "stooq_preview",
                "live_http_performed": True,
                "cache_write_performed": False,
                "raw_response_included": False,
                "response_diagnostics": {"body_kind": "no_data_like"},
            }
        if norm == "BADRAW":
            return {
                "status": "preview_ok",
                "symbol": norm,
                "provider": "stooq_preview",
                "live_http_performed": True,
                "cache_write_performed": False,
                "raw_response_included": True,
            }
        return {
            "status": "http_error",
            "reason": "network_or_timeout",
            "symbol": norm,
            "provider": "stooq_preview",
            "live_http_performed": True,
            "cache_write_performed": False,
            "raw_response_included": False,
        }

    monkeypatch.setattr(upcb, "stooq_live_preview_sanitized_bars", _fake)

    out = upcb.run_stooq_cache_preview_batch(["MSFT", "BADRAW", "QQQ"], live=True)
    assert out["status"] == "batch_preview_ok"
    assert seq == ["MSFT", "BADRAW", "QQQ"]
    o = out["operator_summary"]
    assert o["symbol_mapping_review_count"] == 1  # vendor no-data
    assert o["vendor_format_review_count"] == 0
    assert o["transport_retry_candidate_count"] == 1
    assert o["blocked_cache_write_count"] == 1  # preview_ok + raw flagged
    assert o["needs_api_key_count"] == 0
    assert o["safe_dry_run_count"] == 0


def test_operator_summary_candidate_on_preview_ok(monkeypatch: pytest.MonkeyPatch) -> None:

    monkeypatch.setattr(
        upcb,
        "stooq_live_preview_sanitized_bars",
        lambda *_a, **_k: {
            "status": "preview_ok",
            "symbol": "MSFT",
            "provider": "stooq_preview",
            "live_http_performed": True,
            "cache_write_performed": False,
            "raw_response_included": False,
        },
    )
    out = upcb.run_stooq_cache_preview_batch(["MSFT"], live=True)
    assert out["operator_summary"]["single_symbol_write_candidate_count"] == 1


def test_compute_operator_summary_isolated() -> None:
    rows: list[dict] = [
        {"status": "parse_error", "reason": "stooq_csv_delimiter_drift", "cache_write_allowed": False},
        {"status": "validation_error", "reason": "provider_api_key_required", "cache_write_allowed": False},
        {"status": "validation_error", "reason": "live_http_not_confirmed", "cache_write_allowed": False},
    ]
    o = upcb.compute_operator_summary_from_rows(rows)
    assert o["vendor_format_review_count"] == 1
    assert o["needs_api_key_count"] == 1
    assert o["symbol_mapping_review_count"] == 0


def test_render_us_provider_cache_preview_batch_markdown_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("no HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)
    out = upcb.run_stooq_cache_preview_batch(["MSFT", "GOOGL"], live=False)
    md = upcb.render_us_provider_cache_preview_batch_markdown(out)
    assert md.startswith("# US Provider Batch Preview Summary\n")
    assert "| dry_run | 2 |" in md
    assert "| safe_dry_run_count | 2 |" in md
    assert "## Recommended operator action" in md
    assert "Safe dry-run only" in md
    assert "operator_next_action" not in md
    assert "STOOQ_APIKEY" in md


def test_render_markdown_validation_error_envelope() -> None:
    out = upcb.run_stooq_cache_preview_batch([], live=False)
    md = upcb.render_us_provider_cache_preview_batch_markdown(out)
    assert "empty_symbol_batch" in md
    assert "## Operator summary" in md


def test_cli_batch_markdown_flag_emits_tables(monkeypatch: pytest.MonkeyPatch) -> None:

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("no HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)
    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview-batch",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--markdown",
        ],
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    assert "## Operator summary" in r.stdout
    assert "| dry_run | 1 |" in r.stdout
    assert "{" not in r.stdout


def test_cli_batch_empty_merged_inputs_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("no HTTP")

    monkeypatch.setattr(uplp, "urlopen", _boom)

    r = runner.invoke(
        app,
        ["debug", "us-provider-cache-preview-batch", "--provider", "stooq_preview"],
    )
    assert r.exit_code == 2, r.stdout + r.stderr


def test_cli_batch_write_cache_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def _unused(*_a: object, **_k: object) -> None:
        raise AssertionError("no HTTP")

    monkeypatch.setattr(uplp, "urlopen", _unused)

    r = runner.invoke(
        app,
        [
            "debug",
            "us-provider-cache-preview-batch",
            "--symbols",
            "MSFT",
            "--provider",
            "stooq_preview",
            "--write-cache",
        ],
    )
    assert r.exit_code == 2, r.stdout + r.stderr


def test_makefile_defines_batch_dry_target_and_not_in_safe_push() -> None:
    repo = Path(__file__).resolve().parents[1]
    mf = (repo / "Makefile").read_text(encoding="utf-8")
    assert "us-provider-cache-preview-batch-dry-run:" in mf
    lines = mf.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("safe-push:"):
            tail = "\n".join(lines[i : i + 20])
            assert "us-provider-cache-preview-batch-dry-run" not in tail
            return
    pytest.fail("Makefile missing safe-push")
