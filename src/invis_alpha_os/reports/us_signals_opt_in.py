"""Opt-in US signals dry-run appendix for daily report (explicit manifest only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.data.us_cache_signals_batch_manifest import (
    build_us_cache_signals_previews_from_batch_manifest,
)
from invis_alpha_os.reports.us_signals_dry_run import (
    render_us_cache_signals_multi_symbol_dry_run_section,
)

_OPT_IN_HEADER = "### US Signals Dry Run (opt-in)"
_UNAVAILABLE = (
    f"{_OPT_IN_HEADER}\n\n"
    "*(dry-run skipped: manifest_invalid)*\n\n"
    "- **live_http**: false\n"
)


def append_us_signals_dry_run_section(
    base_markdown: str,
    manifest_path: str | Path,
    *,
    path_base: Path,
) -> str:
    """Append US signals dry-run Markdown when ``manifest_path`` is explicit (opt-in)."""

    result = build_us_cache_signals_previews_from_batch_manifest(
        Path(manifest_path), path_base=path_base
    )
    if result.get("status") != "ok":
        appendix = _UNAVAILABLE
    else:
        previews: list[dict[str, Any]] = list(result.get("previews") or [])
        section = render_us_cache_signals_multi_symbol_dry_run_section(previews)
        section = section.replace(
            "## US Signals Dry Run",
            _OPT_IN_HEADER,
            1,
        ).replace(
            "Not connected to the daily report pipeline.",
            "Appended via `--us-signals-dry-run-manifest` (dry-run only; not buy/sell advice).",
            1,
        )
        appendix = section
    base = base_markdown.rstrip()
    return f"{base}\n\n{appendix}"
