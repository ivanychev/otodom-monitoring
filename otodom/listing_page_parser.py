import base64
import json
import re
from datetime import datetime
from operator import itemgetter
from urllib.parse import urljoin

import pytz
from bs4 import BeautifulSoup
from toolz import concat, unique
from typing_extensions import Self

from otodom.models import Flat

PRICE_RE = re.compile(r"([0-9 ]+)\szł/mc")


def _make_tz_aware(dt: datetime) -> datetime:
    tz = pytz.timezone("Europe/Warsaw")
    return dt.replace(tzinfo=tz)


class OtodomFlatsPageParser:
    def __init__(self, soup: BeautifulSoup, now: datetime, html: str):
        self.soup = soup
        self.now = now
        self.html = html

    @classmethod
    def from_html(cls, html: str, now: datetime) -> Self:
        soup = BeautifulSoup(html, "html.parser")
        return cls(soup=soup, now=now, html=html)

    def is_empty(self) -> bool:
        return bool(self.soup.find_all(attrs={"data-cy": "no-search-results"}))

    def parse(self) -> list[Flat]:
        data = self.soup.find_all(attrs={"id": "__NEXT_DATA__"})
        if not data:
            raise RuntimeError(
                f"Failed to fetch data from from html: base64 {base64.b64encode(self.html.encode('utf8'))}"
            )
        payload: dict = json.loads(data[0].text)

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
        return [
            Flat(
                url=f'https://www.otodom.pl/pl/oferta/{item["slug"]}',
                found_ts=self.now,
                title=item["title"],
                picture_url=item["images"][0]["small"],
                summary_location=item["locationLabel"]["value"],
                price=item["totalPrice"]["value"],
                created_dt=_make_tz_aware(datetime.fromisoformat(item["dateCreated"])),
                pushed_up_dt=datetime.fromisoformat(item["pushedUpAt"])
                if item["pushedUpAt"]
                else None,
            )
            for item in items
        ]
