from datetime import datetime

from pydantic import BaseModel

from otodom.util import dt_to_naive_utc


class Flat(BaseModel):
    url: str
    found_ts: datetime
    title: str | None
    picture_url: str | None
    summary_location: str | None
    price: int | None
    created_dt: datetime | None
    pushed_up_dt: datetime | None

    @property
    def updated_ts(self):
        return dt_to_naive_utc(self.pushed_up_dt or self.created_dt)


class FlatList(BaseModel):
    flats: list[Flat]
