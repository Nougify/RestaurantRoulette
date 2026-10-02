"""Deciding whether a place is open from its OpenStreetMap `opening_hours` text."""

from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from opening_hours import OpeningHours, ParserError

# Opening hours are written in the place's local time, and all the data is Metro Vancouver.
LOCAL_TIMEZONE = ZoneInfo("America/Vancouver")


def local_now() -> datetime:
    """Return the current time in the timezone the opening hours are written in."""
    return datetime.now(LOCAL_TIMEZONE)


@lru_cache(maxsize=4096)
def parse(opening_hours: str) -> OpeningHours | None:
    """Return the parsed schedule, or None if the text is not valid `opening_hours` syntax.

    Many places share the same text ("Mo-Su 11:00-22:00"), so parsed schedules are cached.
    """
    try:
        return OpeningHours(opening_hours)
    except ParserError:
        return None


def is_open(opening_hours: str | None, at: datetime) -> bool:
    """Return True only if the place is known to be open at `at`.

    Missing or unreadable hours count as closed: the site never claims a place is open
    without evidence.
    """
    if opening_hours is None:
        return False
    schedule = parse(opening_hours)
    if schedule is None:
        return False
    if at.tzinfo is not None:
        # The schedule has no timezone of its own; give it the local wall-clock time.
        at = at.astimezone(LOCAL_TIMEZONE).replace(tzinfo=None)
    return schedule.is_open(at)
