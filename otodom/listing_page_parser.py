import base64
import json
import re
from datetime import datetime
from operator import itemgetter
from typing import Self
from urllib.parse import urljoin

import pytz
from bs4 import BeautifulSoup
from loguru import logger
from toolz import concat, unique

from otodom.flat_filter import FlatFilter
from otodom.models import Flat

PRICE_RE = re.compile(r"([0-9 ]+)\szł/mc")


def _make_tz_aware(dt: datetime) -> datetime:
    tz = pytz.timezone("Europe/Warsaw")
    return dt.replace(tzinfo=tz)


def _extract_image_url(item: dict) -> str | None:
    if not item.get("images"):
        return None
    return (
        item["images"][0].get("medium")
        or item["images"][0].get("large")
        or item["images"][0].get("small")
        or None
    )


class OtodomFlatsPageParser:
    def __init__(
        self, soup: BeautifulSoup, now: datetime, html: str, filter: FlatFilter
    ):
        self.soup = soup
        self.now = now
        self.html = html
        self.filter = filter

    @classmethod
    def from_html(cls, html: str, now: datetime, filter: FlatFilter) -> Self:
        soup = BeautifulSoup(html, "html.parser")
        return cls(soup=soup, now=now, html=html, filter=filter)

    def is_empty(self) -> bool:
        return bool(self.soup.find_all(attrs={"data-cy": "no-search-results"}))

    def parse(self) -> list[Flat]:
        data = self.soup.find_all(attrs={"id": "__NEXT_DATA__"})
        if not data:
            raise RuntimeError(
                f"Failed to fetch data from from html: base64 {base64.b64encode(self.html.encode('utf8'))}"
            )
        payload: dict = json.loads(data[0].text)

        if "cala-polska" in payload["props"]["pageProps"]["canonicalURL"]:
            logger.info(
                "Otodom switched to searching across Poland instead of {}, so we exiting...",
                self.filter,
            )
            return []

        items = unique(
            concat(
                [
                    payload["props"]["pageProps"]["data"]["searchAds"]["items"],
                    payload["props"]["pageProps"]["data"]["searchAdsRandomPromoted"][
                        "items"
                    ],
                ]
            ),
            key=itemgetter("id"),
        )
        flats = [
            Flat(
                url=f'https://www.otodom.pl/pl/oferta/{item["slug"]}',
                found_ts=self.now,
                title=item["title"],
                picture_url=_extract_image_url(item),
                summary_location=item["locationLabel"]["value"],
                price=item["totalPrice"]["value"],
                created_dt=_make_tz_aware(datetime.fromisoformat(item["dateCreated"])),
                pushed_up_dt=datetime.fromisoformat(item["pushedUpAt"])
                if item["pushedUpAt"]
                else None,
            )
            for item in items
            if self.filter.matches_filter(item)
        ]
        return flats
