"""Stooq multi-file CSV ingest → canonical manual_jp_bars.csv (no raw row logging)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.data.us_stooq_daily_csv import (
    classify_stooq_csv_text_safely,
    parse_stooq_daily_csv_to_rows,
)
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan
from invis_alpha_os.reports.manual_data_actual_import_approval_package import (
    build_manual_data_actual_import_approval_package,
)
from invis_alpha_os.reports.manual_data_discovery import _location_label, _search_roots
from invis_alpha_os.reports.manual_data_import_flow_dry_run import build_manual_data_import_flow_dry_run
from invis_alpha_os.reports.manual_data_schema_guard import (
    build_manual_data_schema_validation,
    detect_prohibited_headers,
    redacted_header_summary,
)
from invis_alpha_os.reports.stooq_manual_csv_ticker_inference import (
    infer_ticker_from_filename,
    is_stooq_candidate_filename,
)

CONTRACT_DATA_TO = "2026-03-06"
DEFAULT_STOOQ_TARGETS = "5802,6645,285A,5803"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets(csv: str) -> list[str]:
    return [p.strip() for p in csv.split(",") if p.strip()]


def discover_stooq_csv_candidates(
    *,
    search_dirs: list[Path] | None = None,
) -> list[dict[str, Any]]:
    roots = search_dirs if search_dirs is not None else _search_roots()
    found: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            paths = sorted(root.glob("*.csv"), key=lambda p: p.name.lower())
        except OSError:
            continue
        for path in paths:
            if not is_stooq_candidate_filename(path.name):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            inference = infer_ticker_from_filename(resolved)
            try:
                stat = resolved.stat()
                size_bytes = int(stat.st_size)
                modified_at = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            except OSError:
                size_bytes = None
                modified_at = None
            header_preview = ""
            prohibited: list[str] = []
            schema_kind = "unknown"
            try:
                text_head = resolved.read_text(encoding="utf-8", errors="replace")[:4096]
                first_line = text_head.splitlines()[0] if text_head else ""
                headers = [c.strip() for c in first_line.split(",") if c.strip()]
                prohibited = detect_prohibited_headers(headers)
                header_preview = redacted_header_summary(headers)
                meta = classify_stooq_csv_text_safely(text_head)
                schema_kind = "stooq_ohlcv" if meta.get("has_required_columns") else "non_stooq"
            except OSError:
                header_preview = "read_failed"
            found.append(
                {
                    "filename": resolved.name,
                    "directory_label": _location_label(resolved),
                    "file_size_bytes": size_bytes,
                    "modified_at": modified_at,
                    "inferred_ticker": inference.ticker,
                    "inference_confidence": inference.confidence,
                    "inference_reason": inference.reason,
                    "redacted_header_summary": header_preview,
                    "prohibited_columns_detected": bool(prohibited),
                    "prohibited_column_names_redacted": len(prohibited) > 0,
                    "schema_kind": schema_kind,
                    "resolved_path": str(resolved),
                    "path_redacted": True,
                }
            )
    found.sort(key=lambda r: (r.get("inferred_ticker") or "ZZZZ", r["filename"]))
    return found


def _parse_stooq_file(path: Path, ticker: str) -> tuple[list[dict[str, str]], dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if detect_prohibited_headers([c.strip() for c in text.splitlines()[0].split(",") if c.strip()]):
        raise ValueError("prohibited_columns_detected")
    rows = parse_stooq_daily_csv_to_rows(text)
    out: list[dict[str, str]] = []
    for row in rows:
        out.append(
            {
                "ticker": ticker,
                "date": str(row["date"]),
                "open": str(row["open"]),
                "high": str(row["high"]),
                "low": str(row["low"]),
                "close": str(row["close"]),
                "volume": str(int(row["volume"]) if float(row["volume"]).is_integer() else row["volume"]),
            }
        )
    dates = [r["date"] for r in out]
    meta = {
        "ticker": ticker,
        "row_count": len(out),
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "post_contract_row_count": sum(1 for d in dates if d > CONTRACT_DATA_TO),
    }
    return out, meta


def combine_stooq_files_to_manual_jp_bars(
    *,
    file_ticker_pairs: list[tuple[Path, str]],
    output_path: Path,
) -> dict[str, Any]:
    combined: list[dict[str, str]] = []
    per_file: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    duplicate_count = 0
    for path, ticker in file_ticker_pairs:
        rows, meta = _parse_stooq_file(path, ticker)
        added = 0
        for row in rows:
            key = (ticker, row["date"])
            if key in seen_keys:
                duplicate_count += 1
                continue
            seen_keys.add(key)
            combined.append(row)
            added += 1
        meta["rows_written"] = added
        meta["filename"] = path.name
        per_file.append(meta)
    combined.sort(key=lambda r: (r["ticker"], r["date"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ticker", "date", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        writer.writerows(combined)
    dates = [r["date"] for r in combined]
    return {
        "output_path_redacted": True,
        "output_directory_label": _location_label(output_path),
        "output_filename": output_path.name,
        "combined_row_count": len(combined),
        "duplicate_skipped": duplicate_count,
        "date_min": min(dates) if dates else None,
        "date_max": max(dates) if dates else None,
        "post_contract_row_count": sum(1 for d in dates if d > CONTRACT_DATA_TO),
        "per_file": per_file,
        "raw_rows_printed": False,
    }


@dataclass(frozen=True)
class StooqManualCsvIngestV34Result:
    discovery_json: dict[str, Any]
    discovery_markdown: str
    ingest_json: dict[str, Any]
    ingest_markdown: str
    schema_json: dict[str, Any]
    dry_run_json: dict[str, Any]
    import_plan_json: dict[str, Any]
    approval_markdown: str
    approval_json: dict[str, Any]


def build_stooq_manual_csv_ingest_v34(
    *,
    report_date: str,
    repo_root: Path,
    dropzone_dir: Path,
    targets_csv: str = DEFAULT_STOOQ_TARGETS,
    working_dir: Path | None = None,
) -> StooqManualCsvIngestV34Result:
    targets = _parse_targets(targets_csv)
    candidates = discover_stooq_csv_candidates(search_dirs=[dropzone_dir])
    mapping_rows: list[dict[str, Any]] = []
    file_pairs: list[tuple[Path, str]] = []
    unmapped: list[str] = []

    for row in candidates:
        ticker = row.get("inferred_ticker")
        path = Path(str(row["resolved_path"]))
        if row.get("prohibited_columns_detected"):
            mapping_rows.append(
                {
                    "filename": row["filename"],
                    "inferred_ticker": ticker,
                    "confidence": row.get("inference_confidence"),
                    "action": "reject_prohibited_columns",
                }
            )
            continue
        if ticker in targets:
            file_pairs.append((path, str(ticker)))
            mapping_rows.append(
                {
                    "filename": row["filename"],
                    "inferred_ticker": ticker,
                    "confidence": row.get("inference_confidence"),
                    "action": "include",
                }
            )
        elif ticker:
            mapping_rows.append(
                {
                    "filename": row["filename"],
                    "inferred_ticker": ticker,
                    "confidence": row.get("inference_confidence"),
                    "action": "skip_not_in_targets",
                }
            )
        else:
            unmapped.append(row["filename"])
            mapping_rows.append(
                {
                    "filename": row["filename"],
                    "inferred_ticker": None,
                    "confidence": "none",
                    "action": "needs_user_mapping",
                }
            )

    output_path = dropzone_dir / "manual_jp_bars.csv"
    combine_meta: dict[str, Any] = {}
    if len(file_pairs) >= len(targets) and not unmapped:
        combine_meta = combine_stooq_files_to_manual_jp_bars(
            file_ticker_pairs=file_pairs,
            output_path=output_path,
        )
    elif file_pairs:
        combine_meta = combine_stooq_files_to_manual_jp_bars(
            file_ticker_pairs=file_pairs,
            output_path=output_path,
        )
        combine_meta["warning"] = "partial_target_coverage"

    schema_result = build_manual_data_schema_validation(
        input_path=output_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    plan = build_manual_csv_import_plan(
        csv_path=output_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    work = working_dir or (repo_root / "outputs" / "manual_data" / report_date / "stooq_ingest")
    work.mkdir(parents=True, exist_ok=True)
    dry = build_manual_data_import_flow_dry_run(
        input_path=output_path,
        targets_csv=targets_csv,
        report_date=report_date,
        repo_root=repo_root,
        working_dir=work,
        schema_payload=schema_result.json_payload,
    )
    discovery_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v34",
        "candidates_found": len(candidates),
        "stooq_target_files_expected": len(targets),
        "candidates": [{k: v for k, v in c.items() if k != "resolved_path"} for c in candidates],
        "unmapped_filenames": unmapped,
        "secrets_printed": False,
        "raw_rows_printed": False,
    }
    ingest_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v34",
        "ticker_mapping": mapping_rows,
        "combine": combine_meta,
        "targets": targets,
        "contract_data_available_to": CONTRACT_DATA_TO,
        "secrets_printed": False,
        "raw_rows_printed": False,
    }
    selected_candidate = {
        "filename": output_path.name,
        "directory_label": _location_label(output_path),
        "schema_ohlcv_candidate": True,
        "redacted_header_summary": redacted_header_summary(
            ["ticker", "date", "open", "high", "low", "close", "volume"]
        ),
    }
    approval = build_manual_data_actual_import_approval_package(
        report_date=report_date,
        discovery_payload={"selected_candidate": selected_candidate},
        schema_payload=schema_result.json_payload,
        dry_run_payload=dry.json_payload,
    )
    post_approval = {
        **approval.json_payload,
        "pack_version": "v34",
        "source": "stooq_manual_csv_ingest",
        "post_contract_row_count": combine_meta.get("post_contract_row_count"),
    }
    disc_md = "\n".join(
        [
            "# Stooq CSV Candidate Discovery",
            "",
            f"- candidates_found: {len(candidates)}",
            f"- unmapped: {len(unmapped)}",
            "",
            "| file | inferred_ticker | confidence | action |",
            "|---|---|---|---|",
        ]
        + [
            f"| {r['filename']} | {r.get('inferred_ticker') or '-'} | {r.get('confidence')} | {r.get('action')} |"
            for r in mapping_rows
        ]
    )
    ingest_md = "\n".join(
        [
            "# Stooq Manual CSV Ingest Result",
            "",
            f"- combined_row_count: {combine_meta.get('combined_row_count', 0)}",
            f"- date_max: {combine_meta.get('date_max')}",
            f"- post_contract_row_count: {combine_meta.get('post_contract_row_count', 0)}",
            f"- output: {combine_meta.get('output_filename')}",
            "",
        ]
    )
    return StooqManualCsvIngestV34Result(
        discovery_json=discovery_payload,
        discovery_markdown=disc_md,
        ingest_json=ingest_payload,
        ingest_markdown=ingest_md,
        schema_json=schema_result.json_payload,
        dry_run_json=dry.json_payload,
        import_plan_json=plan.json_payload,
        approval_markdown=approval.markdown_text.replace(
            "# Manual Data Actual Import Approval Package",
            "# Post-Contract OHLCV Import Approval Package",
            1,
        ),
        approval_json=post_approval,
    )


def write_stooq_manual_csv_ingest_v34_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: StooqManualCsvIngestV34Result,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    pairs = [
        ("stooq_manual_csv_ingest_result", result.ingest_markdown, result.ingest_json),
        ("post_contract_ohlcv_import_approval_package", result.approval_markdown, result.approval_json),
    ]
    for stem, md, js in pairs:
        for root in (latest, weekly):
            mp = root / f"{stem}.md"
            jp = root / f"{stem}.json"
            mp.write_text(md, encoding="utf-8")
            jp.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"latest_{stem}_md"] = latest / f"{stem}.md"
        paths[f"latest_{stem}_json"] = latest / f"{stem}.json"
    return paths


def sync_stooq_ingest_v34_to_reports_repo(
    *,
    reports_repo_path: Path,
    report_date: str,
    result: StooqManualCsvIngestV34Result,
    registry_md: str,
    registry_json: dict[str, Any],
    coverage_md: str,
    coverage_json: dict[str, Any],
) -> dict[str, Path]:
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    all_pairs = [
        ("stooq_manual_csv_ingest_result", result.ingest_markdown, result.ingest_json),
        ("post_contract_ohlcv_import_approval_package", result.approval_markdown, result.approval_json),
        ("ohlcv_provider_registry_strategy", registry_md, registry_json),
        ("ohlcv_provider_coverage_matrix", coverage_md, coverage_json),
    ]
    for stem, md, js in all_pairs:
        for label, root in (("reports_latest", latest), ("reports_weekly", weekly)):
            mp = root / f"{stem}.md"
            jp = root / f"{stem}.json"
            mp.write_text(md, encoding="utf-8")
            jp.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{stem}_md"] = mp
            paths[f"{label}_{stem}_json"] = jp
    return paths
