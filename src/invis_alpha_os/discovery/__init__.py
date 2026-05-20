"""Cross-sectional discovery (observation-only; no trading recommendations)."""

from invis_alpha_os.discovery.jp_universe_scanner import (
    JpDiscoveryScanResult,
    format_jp_discovery_json,
    format_jp_discovery_markdown,
    scan_jp_universe,
)

__all__ = [
    "JpDiscoveryScanResult",
    "format_jp_discovery_json",
    "format_jp_discovery_markdown",
    "scan_jp_universe",
]
