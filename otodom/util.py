from datetime import datetime
from typing import Any

import pytz


def dt_to_naive_utc(dt: datetime) -> datetime:
    if not dt.tzinfo:
        return dt
    utc_time = dt.astimezone(pytz.utc)
    return utc_time.replace(tzinfo=None)


def is_not_none(x: Any) -> bool:
    return x is not None
