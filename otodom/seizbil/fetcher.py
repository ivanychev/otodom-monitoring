import textwrap
from datetime import datetime

import redis
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from otodom.report import report_message
from otodom.seizbil.parser import fetch_and_parse_offers
from otodom.seizbil.repository import RedisSeizbilRepository, SeizbilRepository
from otodom.telegram_sync import SyncBot


def _report_on_launch(telegram_channel_id: int, bot: SyncBot):
    now = datetime.now()
    msg = f'Hey there, Seizbil crawler bot is reporting! Launching bot at {now.isoformat()}'
    logger.info(msg)
    report_message(bot=bot, telegram_channel_id=telegram_channel_id, message=msg)


def fetch_and_report(selenium_host: str, repo: SeizbilRepository, bot: SyncBot,
                     telegram_channel_id: int):
    offerings = fetch_and_parse_offers(selenium_host)
    logger.info(f'Fetched {len(offerings)} offerings')
    updated = repo.filter_updated(offerings)
    for u in updated:
        bot.send_message(telegram_channel_id, text=textwrap.dedent(f'''\
        New offering at [link]({u.document_url}) with ID `{u.document_id}`.

        Details:
        * `number` = {u.number}
        * `document_url` = {u.document_url}
        * `announcement_date` = {u.announcement_date}
        * `district` = {u.district}
        * `type` = {u.type}
        * `offer_mode` = {u.offer_mode}
        * `submission_start_date` = {u.submission_start_date}
        * `submission_deadline_date` = {u.submission_deadline_date}
        '''), parse_mode='md')
    logger.info(f'Updated {len(updated)}, inserting them...')
    repo.insert(updated)


def fetch_seizbil_offerings_impl(
        redis_host: str,
        redis_port: int,
        selenium_host: str,
        namespace: str,
        every_minutes: int,
        bot: SyncBot,
        telegram_channel_id: int,
):
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    repo = RedisSeizbilRepository(redis_client, namespace=namespace)
    _report_on_launch(
        telegram_channel_id=telegram_channel_id,
        bot=bot
    )
    scheduler = BlockingScheduler()
    scheduler.add_job(
        fetch_and_report,
        'interval',
        minutes=every_minutes,
        id=f'{namespace}_car_fetcher',
        kwargs={
            'repo': repo,
            'selenium_host': selenium_host,
            'bot': bot,
            'telegram_channel_id': telegram_channel_id,
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
            'message': ('Daily check: Seizil crawler bot is still up and running'),
        },
    )
    scheduler.start()
