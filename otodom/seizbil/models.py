import hashlib

import orjson
from cytoolz import valmap
from pydantic import BaseModel

from otodom.helpers import none_to_empty_string


class Offering(BaseModel):
    document_id: str
    number: str | None
    document_url: str | None
    announcement_date: str | None
    district: str | None
    type: str | None
    offer_mode: str | None
    submission_start_date: str | None
    submission_deadline_date: str | None

    def hash(self) -> str:
        # ruff: noqa: S324
        return hashlib.md5(
            orjson.dumps(
                [
                    self.number,
                    self.document_url,
                    self.announcement_date,
                    self.district,
                    self.type,
                    self.offer_mode,
                    self.submission_start_date,
                    self.submission_deadline_date,
                ]
            )
        ).hexdigest()

    def as_dict(self) -> dict:
        d = dict(self)
        d['hash_value'] = self.hash()
        return valmap(none_to_empty_string, d)
