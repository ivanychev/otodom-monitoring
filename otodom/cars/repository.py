from collections.abc import Iterable, Sequence

import redis
from loguru import logger

from otodom.cars.model import CarOffering, DealerMetadata


class CarsRepository:
    def __init__(self, redis_client: redis.Redis, namespace: str):
        self.r = redis_client
        self.namespace = namespace

    def compose_offering_key(self, car_document_id: str) -> str:
        return f'{self.namespace}:offering:{car_document_id}'

    def compose_dealer_key(self, dealer_id: str) -> str:
        return f'{self.namespace}:dealer:{dealer_id}'

    def get_offering(self, car_document_id: str) -> CarOffering | None:
        record = self.r.hgetall(self.compose_offering_key(car_document_id))
        if not record:
            return None
        return CarOffering.from_dict(record)

    def get_dealer(self, dealer_id: str) -> DealerMetadata | None:
        record = self.r.hgetall(self.compose_dealer_key(dealer_id))
        if not record:
            return None
        return DealerMetadata.from_dict(record)

    def save_offering(self, offering: CarOffering):
        key = self.compose_offering_key(offering.car_document_id)
        if self.r.delete(key):
            logger.info('Removed previous offering at {}', key)

        self.r.hset(key, mapping=offering.as_dict())
        logger.info('Saved offering with id {} to key {}', offering.car_document_id, key)

    def save_dealer(self, dealer: DealerMetadata, client: redis.Redis | None = None):
        client = client or self.r
        key = self.compose_dealer_key(dealer.dealer_id)
        if client.delete(key):
            logger.info('Removed previous dealer at {}', key)

        client.hset(key, mapping=dealer.as_dict())
        logger.info('Saved dealer with id {} to key {}', dealer.dealer_id, key)

    def iterate_prefix(self, pattern: str) -> Iterable:
        cursor, values = self.r.scan(match=pattern)
        yield from values
        while cursor:
            cursor, values = self.r.scan(cursor=cursor, match=pattern)
            yield from values

    def keys_count(self) -> int:
        return sum(1 for _ in self.iterate_prefix(f'{self.namespace}:*'))

    def persist_dealers(self, dealers: Sequence[DealerMetadata]):
        dealer_keys = [self.compose_dealer_key(d.dealer_id) for d in dealers]
        existing = [self.r.hgetall(k) for k in dealer_keys]
        with self.r.pipeline() as pipe:
            for dealer, existing_entry in zip(dealers, existing, strict=True):
                if not existing_entry:
                    self.save_dealer(dealer, client=pipe)
            pipe.execute()

    def remove_existing_offerings(
        self, offerings: Sequence[CarOffering]
    ) -> tuple[list[CarOffering], list[CarOffering]]:
        updated_offerings = []
        new_offerings = []
        for o in offerings:
            existing = self.get_offering(o.car_document_id)
            if not existing:
                new_offerings.append(o)
            elif existing.system_updated_at != o.system_updated_at:
                updated_offerings.append(o)
        logger.info(
            'Found {} new and {} updated or new offerings among {}',
            len(new_offerings),
            len(updated_offerings),
            len(offerings),
        )
        return new_offerings, updated_offerings

    @classmethod
    def create(cls, redis_client: redis.Redis, namespare: str):
        repo = cls(redis_client, namespace=namespare)
        logger.info(
            'Created repo, namespace {} contains {} elements',
            namespare,
            repo.keys_count(),
        )
        return repo
