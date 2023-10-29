import requests as r

from otodom.cars.constants import BASE_DATA_SERVICE_URL
from otodom.cars.model import DealerMetadata


def get_dealer_ids() -> list[DealerMetadata]:
    resp = r.get(
        BASE_DATA_SERVICE_URL / 'dealer/showAll',
        params={
            'country': 'PL',
            'category': 'BM',
            'clientid': '66_STOCK_DLO',
            'language': 'pl_PL',
            'stl': 'true',
        },
        timeout=10,
    )
    resp.raise_for_status()
    return [
        DealerMetadata(
            name=record['name'],
            dealer_id=record['attributes']['agDealerCode'],
            country=record['country'],
            state=record['state'],
            city=record['city'],
            street=record['street'],
            postal_code=record['postalCode'],
            latitude=record['lat'],
            longitude=record['lng'],
            homepage=record['attributes']['homepage'],
            mail=record['attributes']['mail'],
        )
        for record in resp.json()['includedDealers']
    ]
