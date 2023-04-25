import pathlib
from datetime import datetime
from operator import attrgetter

import click
import pytz
import timeago
import tqdm
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from telegram import Bot
from telegram.utils.helpers import escape_markdown

from otodom.fetch import fetch_and_persist_flats
from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FILTERS, FlatFilter
from otodom.models import Flat, FlatList
from otodom.report import (
    _send_flat_summary,
    report_error,
    report_message,
    report_new_flats,
)
from otodom.storage import filter_new_flats, init_storage, insert_flats
from otodom.util import dt_to_naive_utc


def _report_on_launch(mode: str, bot_token: str):
    now = datetime.now()
    msg = "\n".join(
        [
            escape_markdown(
                f"Hey there, Zabka reporting! Launching bot at {now.isoformat()}. Active filters:",
                version=2,
            )
        ]
        + [f.get_markdown_description(name) for name, f in FILTERS.items()]
    )
    logger.info(msg)
    report_message(bot_token=bot_token, mode=mode, message=msg)


def _fetch(data_path: str, bot_token: str, send_report: bool, mode: str):
    try:
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
    except Exception as e:
        report_error(bot_token=bot_token, mode=mode, exception=e)
        raise e


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
    _report_on_launch(mode=mode, bot_token=bot_token)
    _fetch(data_path=data_path, bot_token=bot_token, send_report=send_report, mode=mode)


@cli.command()
@click.option(
    "--data-path",
    default=".",
    help="The path to use to store SQLite DB and other data.",
)
@click.option("--bot-token", required=True, help="The Telegram bot token to use.")
@click.option("--send-report", default=True, help="Send report to the Channel.")
@click.option("--mode", default="dev", help="Run mode.")
@click.option("--minutes", default=15, help="Run every.")
def fetch_every(
    data_path: str, bot_token: str, send_report: bool, mode: str, minutes: int
):
    logger.info("Scheduling fetch every {} minutes", minutes)
    _report_on_launch(mode=mode, bot_token=bot_token)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        _fetch,
        "interval",
        minutes=minutes,
        id="fetcher",
        kwargs={
            "data_path": data_path,
            "bot_token": bot_token,
            "send_report": send_report,
            "mode": mode,
        },
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        report_message,
        "cron",
        hour=12,
        kwargs={
            "bot_token": bot_token,
            "mode": mode,
            "message": escape_markdown(
                "Daily check: Zabka Bot is still up and running. Active filters are:\n",
                version=2,
            )
            + "\n".join(
                [f.get_markdown_description(name) for name, f in FILTERS.items()]
            ),
        },
    )
    scheduler.start()


@cli.command()
def print_flats():
    ts = datetime.now().replace(tzinfo=pytz.timezone("Europe/Warsaw"))
    flats = parse_flats_for_filter(
        FlatFilter("warsaw")
        .with_internet()
        .in_muranow()
        .with_air_conditioning()
        .with_max_price(4000)
        .with_min_area(40)
        .with_minimum_build_year(2008),
        now=ts,
    )

    flats.sort(key=attrgetter("updated_ts"), reverse=True)
    logger.info("Fetched {} flats", len(flats))
    for flat in flats:
        logger.info(
            "{}, Flat url: {}",
            timeago.format(flat.updated_ts, dt_to_naive_utc(ts)),
            flat.url,
        )


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
