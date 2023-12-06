import abc
import hashlib
from typing import Collection

import orjson
import redis
from loguru import logger
from pydantic import BaseModel

from otodom.seizbil.models import Offering
from otodom.seizbil.parser import fetch_and_parse_offers

class SeizbilRepository(abc.ABC):
    @abc.abstractmethod
    def filter_updated(self, offerings: Collection[Offering]) -> list[Offering]:
        pass

    @abc.abstractmethod
    def insert(self, offerings: Collection[Offering]) -> None:
        pass


class RedisSeizbilRepository(SeizbilRepository):
    def __init__(self, r: redis.Redis, namespace: str):
        self.r = r
        self.namespace = namespace

    def key_for(self, o: Offering) -> str:
        return self.namespace + ":" + o.document_id

    def filter_updated(self, offerings: Collection[Offering]) -> list[Offering]:
        with self.r.pipeline() as pipe:
            for o in offerings:
                pipe.hgetall(self.key_for(o))
            retrieved = pipe.execute()
        logger.info("Fetched current {} keys, got {} non-nulls", len(retrieved), len([s for s in retrieved if s]))
        updated = []
        for current, saved in zip(offerings, retrieved, strict=True):
            if not saved or current.document_id != saved['document_id']:
                updated.append(current)
        logger.info("Got {} updated records", len(updated))
        return updated

    def insert(self, offerings: Collection[Offering]) -> None:
        with self.r.pipeline() as pipe:
            for o in offerings:
                key = self.key_for(o)
                pipe.delete(key)
                pipe.hset(key, mapping=o.as_dict())
                logger.info('Saved offering with id {} to key {}', o.document_id, key)
            pipe.execute()


if __name__ == "__main__":
    offerings = fetch_and_parse_offers("http://127.0.0.1:4444", limit_pages=3)
    r = redis.StrictRedis(decode_responses=True)
    repo = RedisSeizbilRepository(r, namespace="test_seizill1")
    updated = repo.filter_updated(offerings)
    print(updated)
    repo.insert(updated)

