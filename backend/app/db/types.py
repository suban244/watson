from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from utils.timezone import NEPAL_TZ


class NptDateTime(TypeDecorator[datetime]):
    """`timestamptz` that reads back in Asia/Kathmandu and reads naive input as NPT.

    asyncpg decodes every timestamptz to UTC whatever the session timezone is,
    and converts a naive datetime with the *process's* local zone (UTC in the
    container, NPT on a dev laptop). Converting here means `.date()`,
    `.strftime()` and `relativedelta` all work in the user's wall-clock time.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=NEPAL_TZ)
        return value

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        return value.astimezone(NEPAL_TZ) if value is not None else None
