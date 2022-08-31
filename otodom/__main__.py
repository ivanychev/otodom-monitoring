import pathlib
from datetime import datetime

import click
from loguru import logger

from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FlatFilter
from otodom.report import report_new_flats
from otodom.storage import (
    dump_fetched_flats,
    dump_new_flats,
    filter_new_flats,
    get_total_flats_in_db,
    init_storage,
    insert_flats,
)


@click.command()
@click.option(
    "--data-path",
    default=".",
    help="The path to use to store SQLite DB and other data.",
)
@click.option("--bot-token", required=True, help="The Telegram bot token to use.")
@click.option("--send-report", default=True, help="Send report to the Channel.")
def main(data_path: str, bot_token: str, send_report: bool):
    logger.info("Hey there!")
    data_path = pathlib.Path(data_path).absolute()
    storage_context = init_storage(data_path)
    ts = datetime.now()
    flats = parse_flats_for_filter(
        FlatFilter()
        .with_internet()
        .with_air_conditioning()
        .with_max_price(6000)
        .with_min_area(38)
        .with_minimum_build_year(2010),
        now=ts,
    )
    dump_fetched_flats(flats, storage_context, now=ts)
    logger.info("Fetched {} flats", len(flats))
    new_flats = filter_new_flats(storage_context.sqlite_conn, flats)
    logger.info("Found {} new flats", len(new_flats))
    dump_new_flats(new_flats, storage_context, now=ts)

    insert_flats(storage_context.sqlite_conn, new_flats)
    total_flats = get_total_flats_in_db(storage_context.sqlite_conn)

    if send_report:
        report_new_flats(new_flats, total_flats, bot_token, now=ts)


if __name__ == "__main__":
    main()
