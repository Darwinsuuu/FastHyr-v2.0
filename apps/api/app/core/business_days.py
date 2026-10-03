"""Business days and local times in a workspace's time zone (NOTIFICATIONS.md §1, WORKFLOW.md §5).

Business days skip Saturday and Sunday in the workspace time zone; public holidays are post-MVP.
A delay keeps the local time of day, so a résumé screened on Friday at 10:00 in Manila gets its
rejection email on Tuesday at 10:00 in Manila, whatever that is in UTC.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SATURDAY = 5


def zone_of(name: str | None) -> ZoneInfo:
    """The workspace's time zone; UTC when it has none or the name isn't a known zone."""
    try:
        return ZoneInfo(name) if name else ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def add_business_days(start: datetime, days: int, zone: ZoneInfo) -> datetime:
    """`days` business days after `start`, at the same local time of day, in UTC. A start on a
    weekend counts from the Monday after it: Saturday + 1 is Monday."""
    if start.tzinfo is None:
        raise ValueError("start must be timezone-aware")
    local = start.astimezone(zone)
    day = local.date()
    remaining = days
    while remaining > 0:
        day += timedelta(days=1)
        if day.weekday() < SATURDAY:
            remaining -= 1
    # Rebuild from the wall-clock time so a daylight-saving change in between keeps the hour.
    moved = datetime.combine(day, local.time().replace(tzinfo=None), tzinfo=zone)
    return moved.astimezone(UTC)


def format_local(moment: datetime, zone: ZoneInfo) -> str:
    """A time for an email, e.g. "Fri, 3 Oct 2026, 11:59 PM PST" ([Interview.expiry])."""
    local = moment.astimezone(zone)
    hour = local.hour % 12 or 12
    abbreviation = local.tzname() or "UTC"
    if abbreviation[0] in "+-":
        # Zones with no letter abbreviation, e.g. "+08", read as "GMT+8".
        offset = local.utcoffset() or timedelta()
        minutes = int(offset.total_seconds() // 60)
        sign = "+" if minutes >= 0 else "-"
        hours, rest = divmod(abs(minutes), 60)
        abbreviation = f"GMT{sign}{hours}" + (f":{rest:02d}" if rest else "")
    return (
        f"{local:%a}, {local.day} {local:%b %Y}, {hour}:{local.minute:02d} "
        f"{'AM' if local.hour < 12 else 'PM'} {abbreviation}"
    )
