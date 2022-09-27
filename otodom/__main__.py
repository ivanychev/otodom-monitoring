import pathlib
from datetime import datetime

import click
from loguru import logger
from telegram import Bot

from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FlatFilter
from otodom.models import Flat
from otodom.report import _send_flat_summary, report_new_flats
from otodom.storage import (
    dump_fetched_flats,
    dump_new_flats,
    filter_new_flats,
    get_total_flats_in_db,
    init_storage,
    insert_flats,
)


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--data-path",
    default=".",
    help="The path to use to store SQLite DB and other data.",
)
@click.option("--bot-token", required=True, help="The Telegram bot token to use.")
@click.option("--send-report", default=True, help="Send report to the Channel.")
def fetch(data_path: str, bot_token: str, send_report: bool):
    logger.info("Hey there!")
    data_path = pathlib.Path(data_path).absolute()
    storage_context = init_storage(data_path)
    ts = datetime.now()
    flats = parse_flats_for_filter(
        FlatFilter()
        .with_internet()
        .with_air_conditioning()
        .with_max_price(6500)
        .with_min_area(35)
        .with_minimum_build_year(2008),
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
        report_new_flats(
            new_flats, total_flats, bot_token, now=ts, report_on_no_new_flats=False
        )


@cli.command()
@click.option("--bot-token", required=True, help="The Telegram bot token to use.")
def send_test_flat(bot_token: str):
    bot = Bot(bot_token)
    _send_flat_summary(
        bot,
        Flat(
            url="https://www.otodom.pl/pl/oferta/apartament-w-mennica-residence-grzybowska-od-1-09-ID4i622",
            found_ts=datetime.fromisoformat("2022-08-31T22:54:01.298087"),
            title="Apartament w Mennica Residence Grzybowska /od 1.09",
            picture_url="https://ireland.apollo.olxcdn.com/v1/files/eyJmbiI6ImR4a29sZzhhMDl6MS1BUEwiLCJ3IjpbeyJmbiI6ImVudmZxcWUxYXk0azEtQVBMIiwicyI6IjE0IiwicCI6IjEwLC0xMCIsImEiOiIwIn1dfQ.80v6yvWASzr4MPicf3zpa6U2Ts0PcoFP4P_y7F2oWjI/image;s=655x491;q=80",
            summary_location="Mieszkanie na wynajem: Warszawa, \u015ar\u00f3dmie\u015bcie, ul. Grzybowska",
            price=4500,
        ),
        prefix="Test!!!",
    )


if __name__ == "__main__":
    cli()
