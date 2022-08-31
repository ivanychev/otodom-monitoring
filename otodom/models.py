from datetime import datetime

from pydantic import BaseModel


class Flat(BaseModel):
    url: str
    found_ts: datetime
    title: str | None
    picture_url: str | None
    summary_location: str | None
    price: int | None


class FlatList(BaseModel):
    flats: list[Flat]
