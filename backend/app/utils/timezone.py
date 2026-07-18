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
