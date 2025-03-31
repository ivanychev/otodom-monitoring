from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Self

import requests as r
from loguru import logger

from otodom.cars import CarSearcher
from otodom.cars.constants import BASE_DATA_SERVICE_URL, ENGINE_ELECTRIC, ENGINE_HYBRID
from otodom.cars.model import CarOffering


@dataclass(frozen=True)
class BmwSearchRequestBuilder(CarSearcher):
    degree_of_electrification_based_fuel_type: list[str] | None = None
    start_index: int = 0
    max_results: int = 25
    dealer_ids: list[str] | None = None
    min_price: int | None = None
    max_price: int | None = None
    currency: str = 'PLN'
    description: list[str] = field(default_factory=list)

    def with_electric_fuel_type(self) -> Self:
        c = self.degree_of_electrification_based_fuel_type or []
        c.append(ENGINE_ELECTRIC)
        return replace(
            self,
            degree_of_electrification_based_fuel_type=c,
            description=[*self.description, 'Include vehicles with electric engine'],
        )

    def with_hybrid_fuel_type(self) -> Self:
        c = self.degree_of_electrification_based_fuel_type or []
        c.append(ENGINE_HYBRID)
        return replace(
            self,
            degree_of_electrification_based_fuel_type=c,
            description=[*self.description, 'Include vehicles with hybrid (PHEV) engine'],
        )

    def with_start_index(self, index: int) -> Self:
        return replace(self, start_index=index)

    def with_max_results(self, max_results: int) -> Self:
        return replace(self, max_results=max_results)

    def with_dealer_ids(self, dealer_ids: Iterable[str]) -> Self:
        return replace(self, dealer_ids=list(dealer_ids))

    def with_min_price(self, price: int) -> Self:
        return replace(
            self,
            min_price=price,
            description=[*self.description, f'With min price of {price} {self.currency}'],
        )

    def with_max_price(self, price: int) -> Self:
        return replace(
            self,
            max_price=price,
            description=[*self.description, f'With max price of {price} {self.currency}'],
        )

    def pretty_str(self) -> str:
        return 'BMW car finder:\n' + '\n'.join(f'* {d}' for d in self.description)

    def _get_search_payload(self) -> dict:
        search_context = {'buNos': self.dealer_ids}
        if self.max_price:
            # Price is a list with exactly one dict, so setting it to [{}] as default.
            search_context.setdefault('price', [{}])[0]['maxValue'] = {
                'amount': self.max_price,
                'currency': self.currency,
            }
        if self.min_price:
            search_context.setdefault('price', [{}])[0]['minValue'] = {
                'amount': self.min_price,
                'currency': self.currency,
            }
        if self.degree_of_electrification_based_fuel_type:
            search_context['degreeOfElectrificationBasedFuelType'] = {
                'value': self.degree_of_electrification_based_fuel_type
            }

        return {
            'searchContext': [search_context],
            'resultsContext': {'sort': [{'by': 'PRODUCTION_DATE', 'order': 'ASC'}]},
        }

    def search_result_count(self) -> int:
        search_payload = self._get_search_payload()

        logger.info('Fetching result count ...')
        resp = r.post(
            str(BASE_DATA_SERVICE_URL / 'vehiclesearch/search/pl-pl/stocklocator'),
            params={
                'maxResults': 1,
                'startIndex': 0,
            },
            json=search_payload,
            timeout=10,
        )
        resp.raise_for_status()

        result_count = resp.json()['metadata']['totalCount']
        logger.info('Fetched result count: {}', result_count)
        return result_count

    def search(self) -> list[CarOffering]:
        search_payload = self._get_search_payload()

        logger.info(
            'Fetching search results for start_index {}, max_results {} ...',
            self.start_index,
            self.max_results,
        )

        resp = r.post(
            str(BASE_DATA_SERVICE_URL / 'vehiclesearch/search/pl-pl/stocklocator'),
            params={
                'maxResults': self.max_results,
                'startIndex': self.start_index,
            },
            json=search_payload,
            timeout=10,
        )
        resp.raise_for_status()

        return [
            CarOffering(
                car_document_id=record['vehicle']['documentId'],
                system_updated_at=datetime.fromisoformat(
                    record['vehicle']['internal']['updatedAt']
                ),
                image_urls=sorted(record['vehicle']['media']['cosyImages'].values()),
                dealer_id=record['vehicle']['ordering']['retailData']['buNo'],
                gross_sales_price=float(record['vehicle']['price']['grossSalesPrice']),
                currency=record['vehicle']['price']['listPriceCurrency'],
                model_name=record['vehicle']['vehicleSpecification']['modelAndOption']['model'][
                    'modelDescription'
                ]['en_PL'],
                electrification_type=record['vehicle']['vehicleSpecification'][
                    'technicalAndEmission'
                ]['technicalData']['degreeOfElectrificationBasedFuelType'],
                url=f'https://www.bmw.pl/pl-pl/sl/stocklocator#/details/{record["vehicle"]["documentId"]}',
            )
            for record in resp.json()['hits']
        ]

    def search_all(self) -> list[CarOffering]:
        total_count = self.search_result_count()
        offerings = []

        for start in range(0, total_count, self.max_results):
            end = min(start + self.max_results, total_count)
            delta = end - start
            offerings.extend(self.with_max_results(delta).with_start_index(start).search())
        return offerings
