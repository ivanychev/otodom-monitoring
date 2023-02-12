import pathlib
from datetime import datetime
from operator import attrgetter

import click
import pytz
import timeago
import tqdm
from loguru import logger
from telegram import Bot

from otodom.fetch import fetch_and_persist_flats
from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FILTERS, FlatFilter
from otodom.models import Flat, FlatList
from otodom.report import _send_flat_summary, report_new_flats
from otodom.storage import (
    filter_new_flats,
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
@click.option("--mode", default="dev", help="Run mode.")
def fetch(data_path: str, bot_token: str, send_report: bool, mode: str):
    logger.info("Hey there, Zabka reporting!")
    data_path = pathlib.Path(data_path).absolute()
    storage_context = init_storage(data_path)
    ts = datetime.now()

    for flat_filter in FILTERS.values():
        logger.info("Executing with {} filter", flat_filter.name)
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
                mode=mode,
            )


@cli.command()
def print_flats():
    ts = datetime.now().replace(tzinfo=pytz.timezone("Europe/Warsaw"))
    flats = parse_flats_for_filter(
        FlatFilter("warsaw")
        # .with_internet()
        .in_muranow()
        .with_air_conditioning()
        .with_max_price(6500)
        .with_min_area(40)
        .with_minimum_build_year(2008),
        now=ts,
    )

    flats.sort(key=attrgetter("updated_ts"), reverse=True)
    logger.info("Fetched {} flats", len(flats))
    for flat in flats:
        print(f"{timeago.format(flat.updated_ts, ts)} {flat.url}")


@cli.command()
@click.option(
    "--data-path",
    default=".",
    help="The path to use to store SQLite DB and other data.",
)
def load_from_wal(data_path: str):
    data_path = pathlib.Path(data_path).absolute()
    storage_context = init_storage(data_path)
    fetched_files = list(storage_context.raw_json_path.rglob("fetched_*"))
    logger.info("Found {} fetched JSON files", len(fetched_files))

    url_to_flat = {}
    for fetched_file_path in tqdm.tqdm(fetched_files):
        for flat in FlatList.parse_file(fetched_file_path).flats:
            url_to_flat[flat.url] = flat

    flats = list(url_to_flat.values())
    logger.info("Found {} logged flats", len(flats))

    new_flats = filter_new_flats(storage_context.sqlite_conn, flats)
    insert_flats(storage_context.sqlite_conn, new_flats)


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
