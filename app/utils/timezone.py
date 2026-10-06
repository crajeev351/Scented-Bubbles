"""Timezone utility for Scented Bubbles.
Ensures all server timestamps (which are stored in UTC) are accurately
converted to Indian Standard Time (IST, Asia/Kolkata, UTC+5:30) for display.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

IST_TZ = ZoneInfo("Asia/Kolkata")


def to_ist(dt: datetime | None) -> datetime | None:
    """Converts UTC datetime (aware or naive) into Indian Standard Time (IST, UTC+5:30)."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST_TZ)


def format_ist(dt: datetime | None, fmt: str = "%d %b %Y at %I:%M %p") -> str:
    """Converts UTC datetime to IST and formats cleanly."""
    val = to_ist(dt)
    return val.strftime(fmt) if val else ""
