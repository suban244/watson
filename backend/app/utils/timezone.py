from datetime import datetime
from zoneinfo import ZoneInfo

NEPAL_TZ = ZoneInfo("Asia/Kathmandu")


def now_nepal() -> datetime:
    return datetime.now(NEPAL_TZ)


def parse_date(date_str: str | None) -> datetime | None:
    """Parse a YYYY-MM-DD string into a Nepal-tz datetime.

    Returns now for an empty value and None for an invalid one.
    """
    if not date_str:
        return now_nepal()
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None
    return dt.replace(tzinfo=NEPAL_TZ)


DEFAULT_REMINDER_HOUR = 9


def parse_datetime(
    date_str: str | None, time_str: str | None = None
) -> datetime | None:
    """Parse a YYYY-MM-DD date and optional HH:MM time into a Nepal-tz datetime.

    Defaults to 09:00 NPT when only a date is given. Returns None for an
    invalid date or time.
    """
    date_obj = parse_date(date_str)
    if date_obj is None:
        return None
    if not time_str:
        return date_obj.replace(
            hour=DEFAULT_REMINDER_HOUR, minute=0, second=0, microsecond=0
        )
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return date_obj.replace(hour=hour, minute=minute, second=0, microsecond=0)
