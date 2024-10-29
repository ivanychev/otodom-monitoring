import datetime
import json

import requests
from bs4 import BeautifulSoup
from cytoolz import get_in
from loguru import logger

from otodom.constants import USER_AGENT
from dataclasses import dataclass

@dataclass(frozen=True)
class DetailFlat:
    url: str
    title: str
    created_at: datetime.datetime
    modified_at: datetime.datetime
    building_type: str
    floor_no: str
    area: float
    build_year: int
    price: float
    price_per_m2: float
    image_url: str
    latitude: float
    longitude: float



def parse_flat_page(page_url: str):
    headers = {'User-Agent': USER_AGENT}
    resp = requests.get(page_url, headers=headers, timeout=15)
    html = resp.text
    soup = BeautifulSoup(html, 'html.parser')
    data = soup.find_all(attrs={'id': '__NEXT_DATA__'})
    if not data:
        logger.info("Failed to extract flat from: {}", page_url)
        return None
    payload: dict = json.loads(data[0].text)

    characteristics = {
        item['key']: item
        for item in payload['props']['pageProps']['ad']['characteristics']
    }

    return DetailFlat(
        created_at=datetime.datetime.fromisoformat(payload['props']['pageProps']['ad']['createdAt']),
        modified_at=datetime.datetime.fromisoformat(payload['props']['pageProps']['ad']['modifiedAt']),
        area=float(get_in(['m', 'value'], characteristics, '0')),
        build_year=int(get_in(['build_year', 'value'], characteristics, '0')),
        price=float(get_in(['price', 'value'], characteristics, '0')),
        building_type=get_in(['building_type', 'value'], characteristics, 'UNKNOWN'),
        floor_no=get_in(['floor_no', 'value'], characteristics, '0'),
        price_per_m2=float(get_in(['price_per_m', 'value'], characteristics, '0')),
        title=payload['props']['pageProps']['ad']['title'],
        url=payload['props']['pageProps']['ad']['url'],
        image_url=payload['props']['pageProps']['ad']['images'][0]['medium'],
        latitude=payload['props']['pageProps']['ad']['location']['coordinates']['latitude'],
        longitude=payload['props']['pageProps']['ad']['location']['coordinates']['longitude'],
    )
