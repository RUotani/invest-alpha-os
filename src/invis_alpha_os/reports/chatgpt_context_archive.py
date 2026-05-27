"""Archive helpers for ChatGPT context pack outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_context_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
    write_latest: bool,
    write_archive: bool,
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    yyyy = report_date[:4]
    if write_latest:
        latest = out_dir / "latest"
        latest.mkdir(parents=True, exist_ok=True)
        md = latest / "chatgpt_invest_context_pack.md"
        js = latest / "chatgpt_invest_context_pack.json"
        idx = latest / "index.md"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        idx.write_text(
            "\n".join(
                [
                    "# 最新Context Pack",
                    "",
                    f"- レポート日: {report_date}",
                    f"- 生成日時: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
                    "- 本文: `chatgpt_invest_context_pack.md`",
                    "- JSON: `chatgpt_invest_context_pack.json`",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        paths["latest_md"] = md
        paths["latest_json"] = js
        paths["latest_index"] = idx
    if write_archive:
        arc = out_dir / "archive" / yyyy / report_date
        arc.mkdir(parents=True, exist_ok=True)
        md = arc / "chatgpt_invest_context_pack.md"
        js = arc / "chatgpt_invest_context_pack.json"
        meta = arc / "metadata.json"
        md.write_text(markdown_text, encoding="utf-8")
        js.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        meta.write_text(
            json.dumps(
                {
                    "report_date": report_date,
                    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "source": "weekly_candidate_brief",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        paths["archive_md"] = md
        paths["archive_json"] = js
        paths["archive_metadata"] = meta
    return paths


def sync_to_reports_repo(
    *,
    reports_repo_path: Path,
    repo_root: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    if reports_repo_path.resolve() == repo_root.resolve():
        raise ValueError("reports-repo-path が本体repoと同一です")
    if not reports_repo_path.is_dir():
        raise FileNotFoundError(f"reports repo path が見つかりません: {reports_repo_path}")
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / report_date[:4] / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    latest_md = latest / "chatgpt_invest_context_pack.md"
    latest_json = latest / "chatgpt_invest_context_pack.json"
    latest_idx = latest / "index.md"
    weekly_md = weekly / "chatgpt_invest_context_pack.md"
    weekly_json = weekly / "chatgpt_invest_context_pack.json"
    latest_md.write_text(markdown_text, encoding="utf-8")
    latest_json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    weekly_md.write_text(markdown_text, encoding="utf-8")
    weekly_json.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_idx.write_text(f"# 最新Context Pack\n\n- レポート日: {report_date}\n", encoding="utf-8")
    return {
        "reports_latest_md": latest_md,
        "reports_latest_json": latest_json,
        "reports_latest_index": latest_idx,
        "reports_weekly_md": weekly_md,
        "reports_weekly_json": weekly_json,
    }

