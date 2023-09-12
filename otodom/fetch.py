import pathlib
from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple

from loguru import logger

from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FILTERS, EstateFilter
from otodom.models import Flat
from otodom.report import report_error, report_new_flats
from otodom.storage import (
    StorageContext,
    filter_new_estates,
    get_total_flats_in_db,
    init_storage,
    insert_flats,
    update_flats,
)


class FetchedFlats(NamedTuple):
    new_flats: list[Flat]
    update_flats: list[Flat]
    total_flats: int


def fetch_and_persist_flats(
    storage_context: StorageContext, ts: datetime, flat_filter: EstateFilter
):
    filter_name = flat_filter.name
    flats = parse_flats_for_filter(flat_filter, now=ts)

    logger.info('Fetched {} estates', len(flats))
    new_and_updated_estates = filter_new_estates(
        storage_context.sqlite_conn, flats, filter_name=filter_name
    )
    logger.info('Found {} new estates', len(new_and_updated_estates.new_flats))
    logger.info('Found {} updated estates', len(new_and_updated_estates.updated_flats))

    insert_flats(
        storage_context.sqlite_conn, new_and_updated_estates.new_flats, filter_name
    )
    update_flats(
        storage_context.sqlite_conn, new_and_updated_estates.updated_flats, filter_name
    )
    total_flats = get_total_flats_in_db(storage_context.sqlite_conn, filter_name)
    return FetchedFlats(
        new_flats=new_and_updated_estates.new_flats,
        update_flats=new_and_updated_estates.updated_flats,
        total_flats=total_flats,
    )

def fetch_and_report(data_path: str, bot_token: str, send_report: bool, telegram_channel_id: int,
                     filters: Sequence[str]):
    if not filters:
        raise ValueError('No filters specified')
    try:
        data_path = pathlib.Path(data_path).absolute()
        storage_context = init_storage(data_path)
        ts = datetime.now()
        filters = [FILTERS[name] for name in filters]

        for flat_filter in filters:
            logger.info('Executing with {} filter', flat_filter.name)
            fetched = fetch_and_persist_flats(
                storage_context=storage_context, ts=ts, flat_filter=flat_filter
            )

            if send_report:
                report_new_flats(
                    filter_name=flat_filter.name,
                    new_flats=fetched.new_flats,
                    updated_flats=fetched.update_flats,
                    total_flats=fetched.total_flats,
                    bot_token=bot_token,
                    now=ts,
                    report_on_no_new_flats=False,
                    telegram_channel_id=telegram_channel_id,
                )
        logger.info('Fetch for all filters completed.')
    except Exception as e:
        report_error(bot_token=bot_token, telegram_channel_id=telegram_channel_id, exception=e)
        raise e
