from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.security_dashboard import build_security_dashboard


def test_security_dashboard_aggregates(tmp_path: Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "tests.yml").write_text("name: t\non: push\n", encoding="utf-8")
    result = build_security_dashboard(
        source_repo_path=tmp_path,
        reports_repo_path=None,
        report_date="2026-05-27",
    )
    assert result.json_payload["secrets_printed"] is False
    assert "overall_grade" in result.json_payload
    assert "leakage_audit" in result.json_payload
    assert "source_generated_tracking" in result.json_payload
    assert "github_repo_settings" in result.json_payload


def test_security_dashboard_manual_settings_grade(monkeypatch, tmp_path: Path) -> None:
    from invis_alpha_os.security import security_dashboard as dash_mod

    monkeypatch.setattr(
        dash_mod,
        "build_security_leakage_audit",
        lambda **_: type(
            "R",
            (),
            {
                "json_payload": {
                    "overall_status": "pass",
                    "source_repo": {"suspected_secret_hits": [], "suppressed_false_positive_count": 5},
                }
            },
        )(),
    )
    monkeypatch.setattr(
        dash_mod,
        "build_github_actions_security_audit",
        lambda **_: type("R", (), {"json_payload": {"overall_status": "pass", "findings": []}})(),
    )
    monkeypatch.setattr(
        dash_mod,
        "build_dependency_security_audit",
        lambda: type("R", (), {"json_payload": {"overall_status": "inventory_only"}})(),
    )
    monkeypatch.setattr(
        dash_mod,
        "build_source_generated_tracking_plan",
        lambda **_: type("R", (), {"json_payload": {"tracked_reports_count": 1}})(),
    )
    monkeypatch.setattr(
        dash_mod,
        "build_github_repo_settings_checklist",
        lambda **_: type("R", (), {"json_payload": {"manual_check_required_count": 3, "checks": []}})(),
    )
    monkeypatch.setattr(
        dash_mod,
        "build_manual_data_discovery",
        lambda **_: type(
            "R",
            (),
            {"json_payload": {"safe_to_parse": False, "xlsx_supported": False}, "selected_path": None},
        )(),
    )
    monkeypatch.setattr(
        dash_mod,
        "build_manual_data_export_package",
        lambda **_: type("R", (), {"json_payload": {"required_targets": ["5802"]}})(),
    )
    result = dash_mod.build_security_dashboard(
        source_repo_path=tmp_path,
        reports_repo_path=None,
        report_date="2026-05-27",
    )
    assert result.json_payload["overall_grade"] == "review_required_manual_settings_only"
