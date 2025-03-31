import sqlite3
from collections.abc import Sequence
from datetime import datetime
from operator import attrgetter

import click
import pytz
import timeago
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from tqdm import tqdm

from otodom.cars import fetch_car_offerings_impl
from otodom.fetch import fetch_and_report
from otodom.filter_parser import parse_flats_for_filter
from otodom.flat_filter import FILTERS, EstateFilter
from otodom.flat_page_parser import parse_flat_page
from otodom.models import Flat
from otodom.report import CANONICAL_CHANNEL_IDS, _send_flat_summary, report_message
from otodom.seizbil.fetcher import fetch_seizbil_offerings_impl
from otodom.telegram_sync import SyncBot, escape_markdown
from otodom.util import dt_to_naive_utc


def _parse_channel_id(telegram_channel_id: str):
    return CANONICAL_CHANNEL_IDS.get(telegram_channel_id) or int(telegram_channel_id)


def _report_on_launch(telegram_channel_id: int, bot: SyncBot, filters: Sequence[str]):
    now = datetime.now()
    filters = {f: FILTERS[f] for f in filters}
    msg = '\n'.join(
        [f'Hey there, Zabka reporting! Launching bot at {now.isoformat()}. Active filters:']
        + [f.get_markdown_description(name) for name, f in filters.items()]
    )
    logger.info(msg)
    report_message(bot=bot, telegram_channel_id=telegram_channel_id, message=msg)


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
@click.option('--api-id', type=int, required=True, help='The Telegram API id.')
@click.option('--api-hash', type=str, required=True, help='The Telegram API hash.')
@click.option('--send-report', default=True, help='Send report to the Channel.')
@click.option('--filter', '-f', type=str, multiple=True, help='Names of the filters to use')
@click.option(
    '--telegram-channel-id',
    required=True,
    type=str,
    help='Telegram channel ID. Can be the name of the channel stored in the internal registry (CANONICAL_CHANNEL_IDS).',
)
def fetch(
    data_path: str,
    bot_token: str,
    send_report: bool,
    filter: list[str],
    telegram_channel_id: str,
    api_id: int,
    api_hash: str,
):
    bot = SyncBot.from_bot_token(bot_token=bot_token, api_id=api_id, api_hash=api_hash)
    telegram_channel_id = _parse_channel_id(telegram_channel_id)
    _report_on_launch(telegram_channel_id=telegram_channel_id, bot=bot, filters=filter)
    fetch_and_report(
        data_path=data_path,
        bot=bot,
        send_report=send_report,
        telegram_channel_id=telegram_channel_id,
        filters=filter,
    )


@cli.command()
@click.option(
    '--redis-host',
    required=True,
    help='The Redis host',
)
@click.option(
    '--redis-port',
    default=6379,
    type=int,
    help='The redis port',
)
@click.option(
    '--namespace',
    required=True,
    help='Namespace of the search.',
)
@click.option(
    '--every-minutes',
    required=True,
    type=int,
    help='Interval of scraping.',
)
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
@click.option('--api-id', type=int, required=True, help='The Telegram API id.')
@click.option('--api-hash', type=str, required=True, help='The Telegram API hash.')
@click.option(
    '--telegram-channel-id',
    required=True,
    type=str,
    help='Telegram channel ID. Can be the name of the channel stored in the internal registry (CANONICAL_CHANNEL_IDS).',
)
def fetch_car_offerings(
    redis_host: str,
    redis_port: int,
    namespace: str,
    every_minutes: int,
    api_id: int,
    api_hash: str,
    bot_token: str,
    telegram_channel_id: str,
):
    telegram_channel_id = _parse_channel_id(telegram_channel_id)
    bot = SyncBot.from_bot_token(bot_token=bot_token, api_hash=api_hash, api_id=api_id)
    fetch_car_offerings_impl(
        redis_host,
        redis_port,
        namespace=namespace,
        every_minutes=every_minutes,
        bot=bot,
        telegram_channel_id=telegram_channel_id,
    )


@cli.command()
@click.option(
    '--redis-host',
    required=True,
    help='The Redis host',
)
@click.option(
    '--redis-port',
    default=6379,
    type=int,
    help='The redis port',
)
@click.option(
    '--namespace',
    required=True,
    help='Namespace of the search.',
)
@click.option(
    '--every-minutes',
    required=True,
    type=int,
    help='Interval of scraping.',
)
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
@click.option('--selenium-host', required=True, help='Selenium host to use.')
@click.option('--api-id', type=int, required=True, help='The Telegram API id.')
@click.option('--api-hash', type=str, required=True, help='The Telegram API hash.')
@click.option(
    '--telegram-channel-id',
    required=True,
    type=str,
    help='Telegram channel ID. Can be the name of the channel stored in the internal registry (CANONICAL_CHANNEL_IDS).',
)
def fetch_seizbil_offerings(
    redis_host: str,
    redis_port: int,
    namespace: str,
    every_minutes: int,
    api_id: int,
    api_hash: str,
    bot_token: str,
    telegram_channel_id: str,
    selenium_host: str,
):
    telegram_channel_id = _parse_channel_id(telegram_channel_id)
    bot = SyncBot.from_bot_token(bot_token=bot_token, api_hash=api_hash, api_id=api_id)
    fetch_seizbil_offerings_impl(
        redis_host,
        redis_port,
        selenium_host=selenium_host,
        namespace=namespace,
        every_minutes=every_minutes,
        bot=bot,
        telegram_channel_id=telegram_channel_id,
    )


@cli.command()
@click.option(
    '--data-path',
    default='.',
    help='The path to use to store SQLite DB and other data.',
)
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
@click.option('--api-id', type=int, required=True, help='The Telegram API id.')
@click.option('--api-hash', type=str, required=True, help='The Telegram API hash.')
@click.option(
    '--telegram-channel-id',
    required=True,
    type=str,
    help='Telegram channel ID. Can be the name of the channel stored in the internal registry (CANONICAL_CHANNEL_IDS).',
)
@click.option('--send-report', default=True, help='Send report to the Channel.')
@click.option('--minutes', default=15, help='Run every.')
@click.option('--filter', '-f', type=str, multiple=True, help='Names of the filters to use')
def fetch_every(
    data_path: str,
    send_report: bool,
    minutes: int,
    filter: list[str],
    api_id: int,
    api_hash: str,
    bot_token: str,
    telegram_channel_id: str,
):
    bot = SyncBot.from_bot_token(bot_token=bot_token, api_hash=api_hash, api_id=api_id)
    telegram_channel_id = _parse_channel_id(telegram_channel_id)
    logger.info('Scheduling fetch every {} minutes', minutes)
    _report_on_launch(telegram_channel_id=telegram_channel_id, bot=bot, filters=filter)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        fetch_and_report,
        'interval',
        minutes=minutes,
        id='fetcher',
        kwargs={
            'data_path': data_path,
            'bot': bot,
            'send_report': send_report,
            'telegram_channel_id': telegram_channel_id,
            'filters': filter,
        },
        next_run_time=datetime.now(),
    )
    scheduler.add_job(
        report_message,
        'cron',
        hour=12,
        kwargs={
            'bot': bot,
            'telegram_channel_id': telegram_channel_id,
            'message': escape_markdown(
                'Daily check: Zabka Bot is still up and running. Active filters are:\n',
                version=2,
            )
            + '\n'.join(
                [f.get_markdown_description(name) for name, f in FILTERS.items() if name in filter]
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
    logger.info('Fetched {} estates', len(flats))
    for flat in flats:
        logger.info(
            '{}, Flat url: {}',
            timeago.format(flat.updated_ts, dt_to_naive_utc(ts)),
            flat.url,
        )


@cli.command()
@click.option('--bot-token', required=True, help='The Telegram bot token to use.')
@click.option('--api-id', type=int, required=True, help='The Telegram API id.')
@click.option('--api-hash', type=str, required=True, help='The Telegram API hash.')
def send_test_flat(bot_token: str, api_id: int, api_hash: str):
    bot = SyncBot.from_bot_token(bot_token=bot_token, api_hash=api_hash, api_id=api_id)
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


def parse_flats_gen():
    conn = sqlite3.connect('/Users/iv/Downloads/flats-2.db')
    cursor = conn.cursor()
    result = cursor.execute("""
        SELECT url
        FROM flats
        WHERE filter_name = 'commercial_all_mokotow' """)
    urls = [r[0] for r in result.fetchall()]
    for url in tqdm(urls):
        flat = parse_flat_page(url)
        if flat:
            yield flat


if __name__ == '__main__':
    cli()
