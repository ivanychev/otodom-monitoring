import http
import json
from datetime import datetime
from operator import attrgetter
from time import sleep

import requests as r
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from toolz.itertoolz import unique

from otodom.constants import USER_AGENT
from otodom.flat_filter import FlatFilter
from otodom.listing_page_parser import OtodomFlatsPageParser
from otodom.models import Flat

PAGE_HARD_LIMIT = 100


class RetryableError(Exception):
    pass


@retry(
    retry=retry_if_exception_type(RetryableError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(5),
)
def fetch_listing_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    resp = r.get(url, headers=headers)
    if resp.status_code in (
        http.HTTPStatus.BAD_GATEWAY,
        http.HTTPStatus.SERVICE_UNAVAILABLE,
        http.HTTPStatus.GATEWAY_TIMEOUT,
        http.HTTPStatus.INTERNAL_SERVER_ERROR,
    ):
        raise RetryableError()
    resp.raise_for_status()
    return resp.text


def _infer_page_count(filter: FlatFilter) -> int:
    url = filter.with_page(1).compose_url()
    logger.info("Inferring page count from url: {}", url)
    html = fetch_listing_html(url)
    soup = BeautifulSoup(html, "html.parser")

    data = json.loads(soup.find_all(attrs={"id": "__NEXT_DATA__"})[0].text)
    count = data["props"]["pageProps"]["data"]["searchAds"]["pagination"]["totalPages"]
    return count


def parse_flats_for_filter(
    filter: FlatFilter,
    now: datetime,
    sleep_for: int = 3,
) -> list[Flat]:
    flats = []
    page_count = _infer_page_count(filter)
    logger.info("Inferred that the page count is {}", page_count)
    for page_idx in range(1, page_count + 1):
        sleep(sleep_for)
        url = filter.with_page(page_idx).compose_url()
        logger.info("Querying {}", url)
        html = fetch_listing_html(url)
        parser = OtodomFlatsPageParser.from_html(html, now=now, filter=filter)
        if parser.is_empty():
            break
        parsed_flats = parser.parse()
        if not parsed_flats:
            raise RuntimeError(
                "Looks like there's a next page but the parser failed to parse any flats"
            )
        flats.extend(parser.parse())
    return list(unique(flats, attrgetter("url")))
