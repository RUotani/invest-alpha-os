"""Safe on-disk cache filename slugs (provider-agnostic; no JP watchlist coupling)."""

from __future__ import annotations

import re

_MAX_SLUG_LEN = 64
# Middle may use dot/dash/underscore; ends must be alphanumeric (avoids ".", "..", trailing dots).
_SLUG_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?$")


def sanitize_provider_wire_slug_for_cache_filename(raw: str) -> str:
    """Return a safe single-path-segment slug for ``{slug}.json`` under a cache root.

    Allows ASCII alphanumerics plus ``.``, ``-``, ``_`` (e.g. ``GOOGL``, ``BRK.B``, ``285A``, ``MSFT``).
    Rejects empties, traversal, path separators, control characters, and awkward edge filenames.
    """

    if raw is None:
        raise ValueError("cache wire slug is required")
    s = raw.strip()
    if not s or ".." in s:
        raise ValueError("invalid cache wire slug")
    if "/" in s or "\\" in s:
        raise ValueError("invalid cache wire slug")
    if any(ord(ch) < 32 for ch in s):
        raise ValueError("invalid cache wire slug")
    if len(s) > _MAX_SLUG_LEN:
        raise ValueError("cache wire slug too long")
    if not _SLUG_RE.fullmatch(s):
        raise ValueError("invalid cache wire slug")
    return s
