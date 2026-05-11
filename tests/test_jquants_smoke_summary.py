"""Phase 1a Task 9: sanitized watchlist smoke JSON under outputs/jquants_smoke/."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.reporting.jquants_smoke_summary import (
    build_watchlist_smoke_summary_document,
    sanitize_watchlist_result_rows_for_summary,
    watchlist_smoke_counts_from_results,
)

runner = CliRunner()

_FORBIDDEN_SUBSTRINGS = ("x-api-key", "authorization", "full_url_without_secrets", "query_params")


def test_sanitize_watchlist_rows_strips_sensitive_fields():
    rows = sanitize_watchlist_result_rows_for_summary(
        [
            {
                "code": "7011",
                "status": "dry_run",
                "full_url_without_secrets": "http://masked.example.invalid",
                "query_params": {"date": "20240216"},
                "endpoint_url_without_query": "http://evil",
            },
            {
                "code": "7203",
                "status": "success",
                "row_count": 2,
                "source_key": "data",
                "junk": "x",
            },
        ]
    )
    flat = json.dumps(rows)
    low = flat.lower()
    for s in _FORBIDDEN_SUBSTRINGS:
        assert s not in low
    assert rows[0] == {"code": "7011", "status": "dry_run"}
    assert rows[1]["row_count"] == 2


def test_build_summary_document_shapes():
    cli_out = {
        "status": "dry_run",
        "date": "2024-02-16",
        "date_from": None,
        "date_to": None,
        "target_count": 2,
        "results": [{"code": "7011", "status": "dry_run", "query_params": {}}],
    }
    doc = build_watchlist_smoke_summary_document(cli_out)
    assert doc["raw_response_included"] is False
    assert doc["api_key_displayed"] is False
    assert doc["skipped_count"] == 0
    assert doc["success_count"] == 0
    assert doc["error_count"] == 0
    assert doc["dry_run_count"] == 1
    assert doc["preview_count"] == 0
    assert doc["results"][0]["code"] == "7011"


def test_dry_run_three_rows_match_task_91_expectation():
    cli_out = {
        "status": "dry_run",
        "date": "2024-02-16",
        "target_count": 3,
        "results": [
            {"code": "7011", "status": "dry_run"},
            {"code": "6501", "status": "dry_run"},
            {"code": "6506", "status": "dry_run"},
        ],
    }
    doc = build_watchlist_smoke_summary_document(cli_out)
    assert doc["mode"] == "dry_run"
    assert doc["target_count"] == 3
    assert doc["success_count"] == 0
    assert doc["error_count"] == 0
    assert doc["dry_run_count"] == 3
    assert doc["preview_count"] == 0
    assert doc["skipped_count"] == 0


def test_live_completed_maps_mode_live_and_three_success():
    cli_out = {
        "status": "completed",
        "date": "2024-02-16",
        "target_count": 3,
        "results": [
            {"code": "7011", "status": "success", "row_count": 1, "source_key": "data"},
            {"code": "6501", "status": "success", "row_count": 1, "source_key": "data"},
            {"code": "6506", "status": "success", "row_count": 1, "source_key": "data"},
        ],
    }
    doc = build_watchlist_smoke_summary_document(cli_out)
    assert doc["mode"] == "live"
    assert doc["success_count"] == 3
    assert doc["error_count"] == 0
    assert doc["dry_run_count"] == 0
    assert doc["preview_count"] == 0
    assert doc["skipped_count"] == 0


def test_http_error_increments_error_count_only():
    cli_out = {
        "status": "dry_run",
        "date": "2024-02-16",
        "target_count": 1,
        "results": [{"code": "7011", "status": "http_error", "http_status": 400, "error_body_preview": "x"}],
    }
    doc = build_watchlist_smoke_summary_document(cli_out)
    assert doc["error_count"] == 1
    assert doc["success_count"] == 0
    assert doc["dry_run_count"] == 0
    assert doc["skipped_count"] == 0
    assert doc["preview_count"] == 0


def test_skipped_unsupported_increments_skipped():
    cli_out = {
        "status": "dry_run",
        "date": "2024-02-16",
        "target_count": 2,
        "results": [
            {"code": "285A", "status": "skipped_unsupported_code"},
            {"code": "7011", "status": "dry_run"},
        ],
    }
    doc = build_watchlist_smoke_summary_document(cli_out)
    assert doc["skipped_count"] == 1
    assert doc["dry_run_count"] == 1
    assert doc["error_count"] == 0


def test_preview_top_status_counts_ok_rows_as_preview():
    cli_out = {
        "status": "preview",
        "date": "2024-02-16",
        "target_count": 2,
        "results": [
            {"code": "7011", "status": "ok"},
            {"code": "6501", "status": "validation_error"},
        ],
    }
    doc = build_watchlist_smoke_summary_document(cli_out)
    assert doc["preview_count"] == 1
    assert doc["error_count"] == 1
    assert doc["dry_run_count"] == 0


def test_watchlist_smoke_counts_unknown_status_counts_as_error():
    c = watchlist_smoke_counts_from_results([{"status": "weird_future"}], cli_top_status="dry_run")
    assert c["error_count"] == 1


def test_watchlist_dry_run_save_summary_writes_json(tmp_path, monkeypatch):
    secret = "NEVER_EMBED_THIS_KEY_ABCXYZ"
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_API_KEY", secret)
    out_root = tmp_path / "outputs"
    monkeypatch.setattr("invis_alpha_os.reporting.jquants_smoke_summary.OUTPUTS_DIR", out_root)

    def _boom(*a, **k):
        raise AssertionError("dry-run must not call urlopen")

    with patch(
        "invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_boom
    ):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-watchlist-bars",
                "--date",
                "2024-02-16",
                "--limit",
                "2",
                "--save-summary",
            ],
        )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "dry_run"
    assert "summary_saved_to" in blob
    assert blob["latest_summary_saved_to"]

    smoke_dir = tmp_path / "outputs" / "jquants_smoke"
    stamped = sorted(smoke_dir.glob("watchlist_bars_*_limit2.json"))
    assert len(stamped) == 1
    payload = json.loads(stamped[0].read_text(encoding="utf-8"))
    assert payload["error_count"] == 0
    assert payload["dry_run_count"] == 2
    assert payload["success_count"] == 0
    text = json.dumps(payload)
    assert secret not in text
    low = text.lower()
    for s in _FORBIDDEN_SUBSTRINGS:
        assert s not in low

    latest_path = smoke_dir / "latest.json"
    assert json.loads(latest_path.read_text(encoding="utf-8")) == payload


def test_watchlist_preview_skips_summary_save_even_with_flag(monkeypatch, tmp_path):
    monkeypatch.setattr("invis_alpha_os.reporting.jquants_smoke_summary.OUTPUTS_DIR", tmp_path / "o")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")
    monkeypatch.setenv("JQUANTS_ENABLED", "false")
    r = runner.invoke(
        app,
        [
            "debug",
            "jquants-watchlist-bars",
            "--preview-request",
            "--date",
            "2024-02-16",
            "--limit",
            "1",
            "--save-summary",
        ],
    )
    assert r.exit_code == 0
    blob = json.loads(r.stdout.strip())
    assert blob["status"] == "preview"
    assert "summary_saved_to" not in blob
    jdir = tmp_path / "o" / "jquants_smoke"
    assert not jdir.exists() or not list(jdir.glob("*.json"))


def test_watchlist_live_blocked_save_summary_no_urlopen(monkeypatch, tmp_path):
    monkeypatch.setattr("invis_alpha_os.reporting.jquants_smoke_summary.OUTPUTS_DIR", tmp_path / "o")
    monkeypatch.setenv("JQUANTS_ENABLED", "true")
    monkeypatch.setenv("JQUANTS_ALLOW_LIVE_HTTP", "false")
    monkeypatch.setenv("JQUANTS_API_BASE_URL", "https://jq.test.invalid/v2")

    hits: list[str] = []

    def _trace(*a, **k):
        hits.append("x")

    with patch(
        "invis_alpha_os.data.adapters.jquants_client.urllib.request.urlopen", side_effect=_trace
    ):
        r = runner.invoke(
            app,
            [
                "debug",
                "jquants-watchlist-bars",
                "--live",
                "--date",
                "2024-02-16",
                "--limit",
                "1",
                "--save-summary",
            ],
        )
    assert hits == []
    assert r.exit_code == 1
    blob = json.loads(r.stdout.strip())
    assert blob["summary_saved_to"]
    latest_payload = json.loads((tmp_path / "o" / "jquants_smoke" / "latest.json").read_text(encoding="utf-8"))
    assert latest_payload["error_count"] == 1
    assert latest_payload["dry_run_count"] == 0
    assert (tmp_path / "o" / "jquants_smoke" / "latest.json").is_file()
