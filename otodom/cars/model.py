import json
from copy import copy
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Self

from dacite import from_dict
from toolz import valmap


def none_to_empty_string(s: str | None) -> str:
    return s or ''


@dataclass(frozen=True)
class DealerMetadata:
    name: str
    dealer_id: str
    country: str
    state: str
    city: str
    street: str
    postal_code: str
    latitude: float
    longitude: float
    homepage: str
    mail: str

    def as_dict(self) -> dict:
        d = asdict(self)
        return valmap(none_to_empty_string, d)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        data = copy(data)
        if 'latitude' in data:
            data['latitude'] = float(data['latitude'])
        if 'longitude' in data:
            data['longitude'] = float(data['longitude'])
        return from_dict(data_class=cls, data=data)


@dataclass
class CarOffering:
    car_document_id: str
    system_updated_at: datetime
    model_name: str
    image_urls: list[str]
    dealer_id: str
    gross_sales_price: float
    currency: str
    electrification_type: str

    def get_url(self) -> str:
        return (
            f'https://www.bmw.pl/pl-pl/sl/stocklocator#/details/{self.car_document_id}'
        )

    def as_dict(self) -> dict:
        d = asdict(self)
        d['system_updated_at'] = d['system_updated_at'].isoformat()
        d['image_urls'] = json.dumps(d['image_urls'])
        return valmap(none_to_empty_string, d)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        data = copy(data)
        data['system_updated_at'] = datetime.fromisoformat(data['system_updated_at'])
        data['image_urls'] = json.loads(data['image_urls'])
        if 'gross_sales_price' in data:
            data['gross_sales_price'] = float(data['gross_sales_price'])
        return from_dict(data_class=cls, data=data)
