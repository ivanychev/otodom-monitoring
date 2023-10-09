from datetime import datetime
from itertools import chain

import redis
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from otodom.cars.parse import get_dealer_ids
from otodom.cars.report import report_offering
from otodom.cars.repository import CarsRepository
from otodom.cars.search import BmwSearchRequestBuilder
from otodom.report import report_message
from otodom.telegram_sync import SyncBot


def _report_on_launch(telegram_channel_id: int, bot: SyncBot):
    now = datetime.now()
    msg = f'Hey there, BMW crawler bot is reporting! Launching bot at {now.isoformat()}'
    logger.info(msg)
    report_message(bot=bot, telegram_channel_id=telegram_channel_id, message=msg)

@logger.catch(reraise=True)
def fetch_and_report(
    repo: CarsRepository,
    request_builder: BmwSearchRequestBuilder,
    bot: SyncBot,
    telegram_channel_id: str,
):
    dealers = get_dealer_ids()
    repo.persist_dealers(dealers)
    dealer_id_to_dealers = {d.dealer_id: d for d in dealers}
    offerings = request_builder.search_all()
    new_offerings, updated_offerings = repo.remove_existing_offerings(offerings)

    for o in new_offerings:
        report_offering(
            o,
            dealer_id_to_dealers.get(o.dealer_id),
            'NEW',
            bot=bot,
            telegram_channel_id=telegram_channel_id,
        )
    for o in updated_offerings:
        report_offering(
            o,
            dealer_id_to_dealers.get(o.dealer_id),
            'UPDATED',
            bot=bot,
            telegram_channel_id=telegram_channel_id,
        )
    for o in chain(new_offerings, updated_offerings):
        repo.save_offering(o)


def fetch_car_offerings_impl(
    redis_host: str,
    redis_port: int,
    namespace: str,
    every_minutes: int,
    bot: SyncBot,
    telegram_channel_id: int,
):
    _report_on_launch(
        telegram_channel_id=telegram_channel_id,
        bot=bot
    )
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    repo = CarsRepository.create(redis_client, namespare=namespace)
    request_builder = (
        BmwSearchRequestBuilder().with_electric_fuel_type().with_hybrid_fuel_type()
    )
    scheduler = BlockingScheduler()
    scheduler.add_job(
        fetch_and_report,
        'interval',
        minutes=every_minutes,
        id=f'{namespace}_car_fetcher',
        kwargs={
            'repo': repo,
            'request_builder': request_builder,
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
            'message': 'Daily check: BMW crawler bot is still up and running.',
        },
    )
    scheduler.start()
