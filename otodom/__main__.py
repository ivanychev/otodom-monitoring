import pathlib
from collections.abc import Sequence
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

from otodom.fetch import fetch_and_report
from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FILTERS, EstateFilter
from otodom.models import Flat, FlatList
from otodom.report import (
    CANONICAL_CHANNEL_IDS,
    _send_flat_summary,
    report_message,
)
from otodom.storage import filter_new_estates, init_storage, insert_flats
from otodom.util import dt_to_naive_utc


def _parse_channel_id(telegram_channel_id: str):
    return CANONICAL_CHANNEL_IDS.get(telegram_channel_id) or int(telegram_channel_id)


def _report_on_launch(telegram_channel_id: int, bot_token: str, filters: Sequence[str]):
    now = datetime.now()
    filters = {f: FILTERS[f] for f in filters}
    msg = '\n'.join(
        [
            escape_markdown(
                f'Hey there, Zabka reporting! Launching bot at {now.isoformat()}. Active filters:',
                version=2,
            )
        ]
        + [f.get_markdown_description(name) for name, f in filters.items()]
    )
    logger.info(msg)
    report_message(bot_token=bot_token, telegram_channel_id=telegram_channel_id, message=msg)


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    '--data-path',
    default='.',
    help='The path to use to store SQLite DB and other data.',
)
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
@click.option('--send-report', default=True, help='Send report to the Channel.')
@click.option('--filter', '-f', type=str, multiple=True,
              help='Names of the filters to use')
@click.option(
    '--telegram-channel-id', required=True, type=str, help='Telegram channel ID. Can be the name of the channel stored in the internal registry (CANONICAL_CHANNEL_IDS).'
)
def fetch(data_path: str, bot_token: str, send_report: bool, filter: list[str],
          telegram_channel_id: str):
    telegram_channel_id = _parse_channel_id(telegram_channel_id)
    _report_on_launch(telegram_channel_id=telegram_channel_id, bot_token=bot_token, filters=filter)
    fetch_and_report(data_path=data_path, bot_token=bot_token, send_report=send_report, telegram_channel_id=telegram_channel_id,
                     filters=filter)


@cli.command()
@click.option(
    '--data-path',
    default='.',
    help='The path to use to store SQLite DB and other data.',
)
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
@click.option('--send-report', default=True, help='Send report to the Channel.')
@click.option('--minutes', default=15, help='Run every.')
@click.option('--filter', '-f', type=str, multiple=True,
              help='Names of the filters to use')
@click.option(
    '--telegram-channel-id', required=True, type=str, help='Telegram channel ID. Can be the name of the channel stored in the internal registry (CANONICAL_CHANNEL_IDS).'
)
def fetch_every(
    data_path: str, bot_token: str, send_report: bool, minutes: int,
    telegram_channel_id: str, filter: list[str]
):
    telegram_channel_id = _parse_channel_id(telegram_channel_id)
    logger.info('Scheduling fetch every {} minutes', minutes)
    _report_on_launch(telegram_channel_id=telegram_channel_id, bot_token=bot_token, filters=filter)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        fetch_and_report,
        'interval',
        minutes=minutes,
        id='fetcher',
        kwargs={
            'data_path': data_path,
            'bot_token': bot_token,
            'send_report': send_report,
            'telegram_channel_id': telegram_channel_id,
        },
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        report_message,
        'cron',
        hour=12,
        kwargs={
            'bot_token': bot_token,
            'telegram_channel_id': telegram_channel_id,
            'message': escape_markdown(
                'Daily check: Zabka Bot is still up and running. Active filters are:\n',
                version=2,
            )
            + '\n'.join(
                [f.get_markdown_description(name) for name, f in FILTERS.items()]
            ),
        },
    )
    scheduler.start()


@cli.command()
def print_flats():
    ts = datetime.now().replace(tzinfo=pytz.timezone('Europe/Warsaw'))
    flats = parse_flats_for_filter(
        EstateFilter('warsaw')
        .rent_a_flat()
        .with_internet()
        .in_ochota()
        .with_air_conditioning()
        .with_max_price(4000)
        .with_min_area(40)
        .with_minimum_build_year(2008),
        now=ts,
    )

    flats.sort(key=attrgetter('updated_ts'), reverse=True)
    logger.info('Fetched {} flats', len(flats))
    for flat in flats:
        logger.info(
            '{}, Flat url: {}',
            timeago.format(flat.updated_ts, dt_to_naive_utc(ts)),
            flat.url,
        )


@cli.command()
@click.option(
    '--data-path',
    default='.',
    help='The path to use to store SQLite DB and other data.',
)
def load_from_wal(data_path: str):
    data_path = pathlib.Path(data_path).absolute()
    storage_context = init_storage(data_path)
    fetched_files = list(storage_context.raw_json_path.rglob('fetched_*'))
    logger.info('Found {} fetched JSON files', len(fetched_files))

    url_to_flat = {}
    for fetched_file_path in tqdm.tqdm(fetched_files):
        for flat in FlatList.parse_file(fetched_file_path).flats:
            url_to_flat[flat.url] = flat

    flats = list(url_to_flat.values())
    logger.info('Found {} logged flats', len(flats))

    new_flats = filter_new_estates(storage_context.sqlite_conn, flats)
    insert_flats(storage_context.sqlite_conn, new_flats)


@cli.command()
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
def send_test_flat(bot_token: str):
    bot = Bot(bot_token)
    _send_flat_summary(
        bot,
        Flat(
            url='https://www.otodom.pl/pl/oferta/apartament-w-mennica-residence-grzybowska-od-1-09-ID4i622',
            found_ts=datetime.fromisoformat('2022-08-31T22:54:01.298087'),
            title='Apartament w Mennica Residence Grzybowska /od 1.09',
            picture_url='https://ireland.apollo.olxcdn.com/v1/files/eyJmbiI6ImR4a29sZzhhMDl6MS1BUEwiLCJ3IjpbeyJmbiI6ImVudmZxcWUxYXk0azEtQVBMIiwicyI6IjE0IiwicCI6IjEwLC0xMCIsImEiOiIwIn1dfQ.80v6yvWASzr4MPicf3zpa6U2Ts0PcoFP4P_y7F2oWjI/image;s=655x491;q=80',
            summary_location='Mieszkanie na wynajem: Warszawa, \u015ar\u00f3dmie\u015bcie, ul. Grzybowska',
            price=4500,
        ),
        prefix='Test!!!',
    )


if __name__ == '__main__':
    cli()
