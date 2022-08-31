import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag
from loguru import logger
from typing_extensions import Self

from otodom.constants import BASE_URL
from otodom.models import Flat

PRICE_RE = re.compile(r"([0-9 ]+)\szł/mc")


class OtodomFlatsPageParser:
    def __init__(self, soup: BeautifulSoup, now: datetime):
        self.soup = soup
        self.now = now

    @classmethod
    def from_html(cls, html: str, now: datetime) -> Self:
        soup = BeautifulSoup(html, "html.parser")
        return cls(soup=soup, now=now)

    def is_empty(self) -> bool:
        return bool(self.soup.find_all(attrs={"data-cy": "no-search-results"}))

    def parse(self) -> list[Flat]:
        cards = self.soup.find_all(attrs={"data-cy": "listing-item-link"})
        return [self._parse_card(card) for card in cards]

    def get_card(self, html: str, index: int) -> Tag:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all(attrs={"data-cy": "listing-item-link"})
        return cards[index]

    def _parse_card(self, card: Tag) -> Flat:
        return Flat(
            url=urljoin(BASE_URL, card.attrs["href"]),
            found_ts=self.now,
            picture_url=self._parse_image_url(card),
            summary_location=self._parse_summary_location(card),
            title=self._parse_title(card),
            price=self._parse_price(card),
        )

    def _parse_price(self, card: Tag) -> int | None:
        try:
            raw_price = (
                card.find_all("article")[0].findChildren("div", recursive=False)[1].text
            )
            raw_price = PRICE_RE.findall(raw_price)[0]
            raw_price = re.sub(r"\s", "", raw_price)
            return int(raw_price)
        except IndexError as e:
            logger.exception(
                "Failed to parse price, raw_price: {} , card: {}", raw_price, card
            )
            return None
        except Exception as e:
            logger.exception("Failed to parse price, card: {}", card)
            return None

    def _parse_image_url(self, card: Tag) -> str | None:
        try:
            return str(card.find_all("picture")[0].find_all("source")[0]["srcset"])
        except Exception as e:
            logger.exception("Failed to parse picture, card: {}", card)
            return None

    def _parse_title(self, card: Tag) -> str | None:
        try:
            return str(
                card.find_all("article")[0].findChildren("div", recursive=False)[0].text
            )
        except Exception as e:
            logger.exception("Failed to parse title, card: {}", card)
            return None

    def _parse_summary_location(self, card: Tag) -> str | None:
        try:
            return str(
                card.find_all("article")[0].findChildren("p", recursive=False)[0][
                    "title"
                ]
            )
        except Exception as e:
            logger.exception("Failed to parse location, card: {}", card)
            return None
