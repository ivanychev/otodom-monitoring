import base64
import json
import re
from datetime import datetime
from operator import itemgetter
from typing import Self

import pytz
from bs4 import BeautifulSoup
from toolz import concat, unique

from otodom.flat_filter import EstateFilter
from otodom.models import Flat

PRICE_RE = re.compile(r'([0-9 ]+)\szł/mc')


def _make_tz_aware(dt: datetime) -> datetime:
    tz = pytz.timezone('Europe/Warsaw')
    return dt.replace(tzinfo=tz)


def _extract_image_url(item: dict) -> str | None:
    if not item.get('images'):
        return None
    return (
        item['images'][0].get('medium')
        or item['images'][0].get('large')
        or item['images'][0].get('small')
        or None
    )


class ParsedDataError(Exception):
    def __init__(
        self, message: str, data: dict, uploaded_filename: str = 'context.json'
    ):
        self.data = data
        self.message = message
        self.uploaded_filename = uploaded_filename
        super().__init__(self.message)

class LocationNotAvailableError(Exception):
    pass


class OtodomFlatsPageParser:
    def __init__(
        self, soup: BeautifulSoup, now: datetime, html: str, filter: EstateFilter
    ):
        self.soup = soup
        self.now = now
        self.html = html
        self.filter = filter

    @classmethod
    def from_html(cls, html: str, now: datetime, filter: EstateFilter) -> Self:
        soup = BeautifulSoup(html, 'html.parser')
        return cls(soup=soup, now=now, html=html, filter=filter)

    def is_empty(self) -> bool:
        return bool(self.soup.find_all(attrs={'data-cy': 'no-search-results'}))

    def parse(self) -> list[Flat]:
        data = self.soup.find_all(attrs={'id': '__NEXT_DATA__'})
        if not data:
            raise RuntimeError(
                f"Failed to fetch data from from html: base64 {base64.b64encode(self.html.encode('utf8'))}"
            )
        payload: dict = json.loads(data[0].text)
        data = payload['props']['pageProps']['data']
        if not data:
            context = payload | {'__html': self.html}
            raise ParsedDataError(
                data=context,
                message='The $.props.pageProps.data is empty',
                uploaded_filename='page_next_data.json',
            )

        items = unique(
            concat(
                [
                    data['searchAds']['items'],
                    (data.get('searchAdsRandomPromoted') or {}).get('items', ()),
                ]
            ),
            key=itemgetter('id'),
        )
        return [
            Flat(
                url=f'https://www.otodom.pl/pl/oferta/{item["slug"]}',
                found_ts=self.now,
                title=item['title'],
                picture_url=_extract_image_url(item),
                summary_location=_get_item_summary_location(item),
                price=int(item['totalPrice']['value']),
                created_dt=_make_tz_aware(datetime.fromisoformat(item['dateCreated'])),
                pushed_up_dt=datetime.fromisoformat(item['pushedUpAt'])
                if item['pushedUpAt']
                else None,
            )
            for item in items
            if self.filter.matches_filter(item)
        ]


def _get_item_summary_location(item: dict) -> str:
    if 'location' not in item:
        raise LocationNotAvailableError
    location_names = [
        row['fullName']
        for row in item['location'].get('reverseGeocoding', {}).get('locations', ())
    ]
    return ' '.join(reversed(location_names))
