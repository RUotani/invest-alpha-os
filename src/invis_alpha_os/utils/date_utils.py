"""JST calendar date strings without ``tzdata`` / ``ZoneInfo`` (Hotfix A).

Uses a fixed UTC+9 offset. Intended for **Japan-market report filenames** (``daily``, ``pack``)
so GitHub Actions (UTC) and local runs agree on the **same calendar day label** for JP outputs.

Smoke JSON ``created_at`` timestamps remain **UTC** elsewhere — see ``reporting/jquants_smoke_summary.py``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

_JST = timezone(timedelta(hours=9))


def date_jst_iso(now: datetime | None = None) -> str:
    """Return ``YYYY-MM-DD`` for the JST (+09:00 fixed) calendar date.

    If *now* is omitted, the instant is taken from ``datetime.now(timezone.utc)`` (CI-friendly),
    then converted to JST. *now* must be timezone-aware if provided.
    """

    current = now if now is not None else datetime.now(timezone.utc)
    if current.tzinfo is None:
        msg = "date_jst_iso(now=...) requires a timezone-aware datetime"
        raise ValueError(msg)
    return current.astimezone(_JST).date().isoformat()


def today_jst_iso() -> str:
    return date_jst_iso()
