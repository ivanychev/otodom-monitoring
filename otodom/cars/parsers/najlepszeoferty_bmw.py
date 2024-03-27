import enum
import http
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Self, TypedDict

import requests as r
from bs4 import BeautifulSoup
from cytoolz import valfilter
from loguru import logger

from otodom.cars.model import CarOffering
from otodom.cars.parsers.car_searcher import CarSearcher
from otodom.util import is_not_none

SEARCH_ENDPOINT = 'https://najlepszeoferty.bmw.pl/uzywane/api/v1/ems/bmw-used-pl_PL/search'
MAX_RESULTS_IN_BATCH = 23


class Brand(enum.IntEnum):
    BMW = 1
    MINI = 65


class EngineType(enum.IntEnum):
    # These values might change. In such event, look them up
    # when searching stuff on https://najlepszeoferty.bmw.pl/uzywane/wyszukaj
    ELECTRIC = 3
    HYBRID_GASOLINE = 4
    GASOLINE = 1
    HYBRID_DIESEL = 6


class GenericEquipment(enum.IntEnum):
    HEATING_OF_DRIVING_WHEEL = 234


class GearboxType(enum.Enum):
    AUTOMATIC = 'AUT'
    MANUAL = 'SCH'


OrDict = TypedDict('OrDict', {'$or': list})


def _build_or_matcher_from_list_of_options(values: list[enum.Enum]) -> Any | OrDict:
    return values[0].value if len(values) == 1 else {'$or': [v.value for v in values]}


def _build_and_matcher_from_list_of_options(values: list[enum.Enum]) -> Any | OrDict:
    return values[0].value if len(values) == 1 else {'$and': [v.value for v in values]}


def get_car_images_from_url(url: str) -> list[str]:
    logger.info('Fetching and parsing HTML from {}', url)
    resp = r.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, features='html.parser')
    elements = soup.select('.link-img')
    return [
        elem.attrs['data-srcset'].split(' ', maxsplit=1)[0]
        for elem in elements
        if elem.has_attr('data-srcset')
    ]


@dataclass(frozen=True)
class UserBmwCarsSearchRequestBuilder(CarSearcher):
    brand: Brand = Brand.BMW
    min_price: int = 0
    max_price: int = 1250000
    min_doors: int | None = None
    max_doors: int | None = None
    min_mileage: int | None = None
    max_mileage: int | None = None
    engine_types: list[EngineType] = field(default_factory=list)
    gearbox_types: list[GearboxType] = field(default_factory=list)
    generic_equipment: list[GenericEquipment] = field(default_factory=list)
    verbose_description: list[str] = field(default_factory=list)

    def with_max_price(self, max_price_pln: int) -> Self:
        return replace(
            self,
            max_price=max_price_pln,
            verbose_description=[*self.verbose_description, f'With max price of {max_price_pln}'],
        )

    def include_electric_engines(self):
        return replace(
            self,
            engine_types=[*self.engine_types, EngineType.ELECTRIC],
            verbose_description=[*self.verbose_description, 'With fully electric engine.'],
        )

    def include_gasoline_hybrids(self):
        return replace(
            self,
            engine_types=[*self.engine_types, EngineType.HYBRID_GASOLINE],
            verbose_description=[*self.verbose_description, 'With hybrid gasoline engine.'],
        )

    def include_gasoline(self):
        return replace(
            self,
            engine_types=[*self.engine_types, EngineType.GASOLINE],
            verbose_description=[*self.verbose_description, 'With gasoline engine.'],
        )

    def include_diesel_hybrids(self):
        return replace(
            self,
            engine_types=[*self.engine_types, EngineType.HYBRID_DIESEL],
            verbose_description=[*self.verbose_description, 'With hybrid diesel engine.'],
        )

    def include_automatic_gearbox(self):
        return replace(
            self,
            gearbox_types=[*self.gearbox_types, GearboxType.AUTOMATIC],
            verbose_description=[*self.verbose_description, 'With automatic gearbox.'],
        )

    def include_manual_gearbox(self):
        return replace(
            self,
            gearbox_types=[*self.gearbox_types, GearboxType.MANUAL],
            verbose_description=[*self.verbose_description, 'With manual gearbox.'],
        )

    def with_min_doors(self, min_doors):
        return replace(
            self,
            min_doors=min_doors,
            verbose_description=[*self.verbose_description, f'With minimum of {min_doors} doors.'],
        )

    def with_max_doors(self, max_doors):
        return replace(
            self,
            max_doors=max_doors,
            verbose_description=[*self.verbose_description, f'With maximum of {max_doors} doors.'],
        )

    def with_min_mileage(self, min_mileage):
        return replace(
            self,
            min_mileage=min_mileage,
            verbose_description=[
                *self.verbose_description,
                f'With minimum of {min_mileage} mileage.',
            ],
        )

    def with_max_mileage(self, max_mileage):
        return replace(
            self,
            max_mileage=max_mileage,
            verbose_description=[
                *self.verbose_description,
                f'With maximum of {max_mileage} mileage.',
            ],
        )

    def with_driving_wheel_heating(self):
        return replace(
            self,
            generic_equipment=[*self.generic_equipment, GenericEquipment.HEATING_OF_DRIVING_WHEEL],
            verbose_description=[*self.verbose_description, 'With heating of the driving wheel.'],
        )

    def _build_search_payload(self, skip: int = 0, limit: int = 23) -> dict:
        match = {
            'brand': self.brand.value,
            'transactionalPrice': {'$min': self.min_price, '$max': self.max_price},
        }
        if self.gearbox_types:
            match['transmission'] = _build_or_matcher_from_list_of_options(self.gearbox_types)
        if self.engine_types:
            match['fuel'] = _build_or_matcher_from_list_of_options(self.engine_types)
        if self.generic_equipment:
            match['genericEquipment'] = _build_and_matcher_from_list_of_options(
                self.generic_equipment
            )
        if self.min_mileage is not None or self.max_mileage is not None:
            match['mileage'] = valfilter(
                is_not_none, {'$min': self.min_mileage, '$max': self.max_mileage}
            )
        if self.min_doors is not None or self.max_doors is not None:
            match['doors'] = valfilter(
                is_not_none, {'$min': self.min_doors, '$max': self.max_doors}
            )

        return {'$limit': limit, '$skip': skip, '$match': match}

    def _get_raw_search_result(self, skip: int = 0, limit: int = 23) -> dict:
        payload = self._build_search_payload(skip=skip, limit=limit)
        logger.info('Issuing search request to {}', SEARCH_ENDPOINT)
        resp = r.post(SEARCH_ENDPOINT, json=payload, timeout=10)
        if resp.status_code != http.HTTPStatus.OK:
            raise RuntimeError(
                f'HTTP request failed with status {resp.status_code} and contents {resp.text}'
            )
        return resp.json()

    def search_result_count(self) -> int:
        payload = self._get_raw_search_result(limit=1)
        return int(payload['$count']['$total'])

    def search_all(self) -> list[CarOffering]:
        results_count = self.search_result_count()
        offerings = []

        for start in range(0, results_count, MAX_RESULTS_IN_BATCH):
            end = min(start + MAX_RESULTS_IN_BATCH, results_count)
            limit = end - start
            offerings.extend(self._get_raw_search_result(skip=start, limit=limit)['$list'])
        return [
            CarOffering(
                car_document_id=str(o['id']),
                system_updated_at=datetime.fromisoformat(o['created']),
                model_name=o['title'],
                image_urls=get_car_images_from_url(
                    f"https://najlepszeoferty.bmw.pl/uzywane/wyszukaj/opis-szczegolowy/{o['id']}"
                ),
                dealer_id=o['dealer']['id'],
                gross_sales_price=o['transactionalPrice'],
                currency='PLN',
                electrification_type=o['fuel']['label'],
                url=f"https://najlepszeoferty.bmw.pl/uzywane/wyszukaj/opis-szczegolowy/{o['id']}",
            )
            for o in offerings
        ]

    def pretty_str(self) -> str:
        return '\n'.join(self.verbose_description)
