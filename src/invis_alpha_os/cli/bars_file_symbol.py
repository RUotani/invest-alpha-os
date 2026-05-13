"""Generic symbol labels for CLI inputs (bars-file mode — not JP wire validation)."""

from __future__ import annotations

from invis_alpha_os.data.cache_wire_slug import sanitize_provider_wire_slug_for_cache_filename


def normalize_generic_bars_file_symbol_label(raw: str) -> str:
    """Strip and validate a display/cache-style symbol token (Observation-only tooling)."""

    return sanitize_provider_wire_slug_for_cache_filename(raw)
