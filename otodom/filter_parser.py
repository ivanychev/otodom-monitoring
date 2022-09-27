from datetime import datetime
from operator import attrgetter
from time import sleep

from loguru import logger
from toolz.itertoolz import unique

from otodom.fetch import fetch_listing_html
from otodom.flat_filter import FlatFilter
from otodom.listing_page_parser import OtodomFlatsPageParser
from otodom.models import Flat

PAGE_HARD_LIMIT = 100


def parse_flats_for_filter(
    filter: FlatFilter,
    now: datetime,
    sleep_for: int = 3,
) -> list[Flat]:
    page_idx = 0
    flats = []
    while True:
        sleep(sleep_for)
        page_idx += 1
        url = filter.with_page(page_idx).compose_url()
        logger.info("Querying {}", url)
        html = fetch_listing_html(url)
        parser = OtodomFlatsPageParser.from_html(html, now=now)
        if parser.is_empty():
            break
        parsed_flats = parser.parse()
        if not parsed_flats:
            raise RuntimeError(
                "Looks like there's a next page but the parser failed to parse any flats"
            )
        flats.extend(parser.parse())
    return list(unique(flats, attrgetter("url")))
