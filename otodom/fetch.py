from datetime import datetime
from typing import NamedTuple

from loguru import logger

from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FlatFilter
from otodom.models import Flat
from otodom.storage import (
    StorageContext,
    dump_fetched_flats,
    dump_new_flats,
    dump_updated_flats,
    filter_new_flats,
    get_total_flats_in_db,
    insert_flats,
    update_flats,
)


class FetchedFlats(NamedTuple):
    new_flats: list[Flat]
    update_flats: list[Flat]
    total_flats: int


def fetch_and_persist_flats(
    storage_context: StorageContext, ts: datetime, flat_filter: FlatFilter
):
    filter_name = flat_filter.name
    flats = parse_flats_for_filter(flat_filter, now=ts)
    dump_fetched_flats(flats, filter_name, storage_context, now=ts)

    logger.info("Fetched {} flats", len(flats))
    new_and_updated_flats = filter_new_flats(
        storage_context.sqlite_conn, flats, filter_name=filter_name
    )
    logger.info("Found {} new flats", len(new_and_updated_flats.new_flats))
    logger.info("Found {} updated flats", len(new_and_updated_flats.updated_flats))

    dump_new_flats(
        new_and_updated_flats.new_flats, filter_name, storage_context, now=ts
    )
    dump_updated_flats(
        new_and_updated_flats.updated_flats, filter_name, storage_context, now=ts
    )

    insert_flats(
        storage_context.sqlite_conn, new_and_updated_flats.new_flats, filter_name
    )
    update_flats(
        storage_context.sqlite_conn, new_and_updated_flats.updated_flats, filter_name
    )
    total_flats = get_total_flats_in_db(storage_context.sqlite_conn, filter_name)
    return FetchedFlats(
        new_flats=new_and_updated_flats.new_flats,
        update_flats=new_and_updated_flats.updated_flats,
        total_flats=total_flats,
    )
