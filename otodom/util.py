from datetime import datetime

import pytz


def dt_to_naive_utc(dt: datetime) -> datetime:
    if not dt.tzinfo:
        return dt
    utc_time = dt.astimezone(pytz.utc)
    return utc_time.replace(tzinfo=None)
