"""Cross-sectional discovery (observation-only; no trading recommendations)."""

from invis_alpha_os.discovery.cross_market_contract import (
    SCHEMA_VERSION,
    merge_cross_market_json_payloads,
)
from invis_alpha_os.discovery.jp_universe_scanner import (
    JpDiscoveryScanResult,
    format_jp_discovery_json,
    format_jp_discovery_markdown,
    scan_jp_universe,
)
from invis_alpha_os.discovery.us_universe_scanner import (
    UsDiscoveryScanResult,
    format_us_discovery_json,
    format_us_discovery_markdown,
    scan_us_universe,
)

__all__ = [
    "JpDiscoveryScanResult",
    "UsDiscoveryScanResult",
    "SCHEMA_VERSION",
    "format_jp_discovery_json",
    "format_jp_discovery_markdown",
    "format_us_discovery_json",
    "format_us_discovery_markdown",
    "merge_cross_market_json_payloads",
    "scan_jp_universe",
    "scan_us_universe",
]
