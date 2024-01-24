from datetime import datetime
from itertools import chain

import redis
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from otodom.cars.parsers.car_searcher import CarSearcher
from otodom.cars.parsers.najlepszeoferty_bmw import UserBmwCarsSearchRequestBuilder
from otodom.cars.parsers.stolodataservice import BmwSearchRequestBuilder
from otodom.cars.report import report_offering
from otodom.cars.repository import CarsRepository
from otodom.report import report_message
from otodom.telegram_sync import SyncBot


def _report_on_launch(telegram_channel_id: int, bot: SyncBot, request_builder: CarSearcher):
    now = datetime.now()
    msg = f'Hey there, BMW crawler bot is reporting! Launching bot at {now.isoformat()}. Using query:\n\n{request_builder.pretty_str()}'
    logger.info(msg)
    report_message(bot=bot, telegram_channel_id=telegram_channel_id, message=msg)


@logger.catch(reraise=True)
def fetch_and_report(
        repo: CarsRepository,
        request_builder: CarSearcher,
        bot: SyncBot,
        telegram_channel_id: str,
):
    offerings = request_builder.search_all()
    new_offerings, updated_offerings = repo.remove_existing_offerings(offerings)

    for o in new_offerings:
        report_offering(
            o,
            'NEW',
            bot=bot,
            telegram_channel_id=telegram_channel_id,
        )
    for o in updated_offerings:
        report_offering(
            o,
            'UPDATED',
            bot=bot,
            telegram_channel_id=telegram_channel_id,
        )
    for o in chain(new_offerings, updated_offerings):
        repo.save_offering(o)


def get_new_bmw_searcher() -> BmwSearchRequestBuilder:
    return BmwSearchRequestBuilder().with_electric_fuel_type().with_hybrid_fuel_type().with_max_price(400000)


def get_used_bmw_searcher() -> BmwSearchRequestBuilder:
    return (UserBmwCarsSearchRequestBuilder()
            .with_max_price(300000)
            .include_automatic_gearbox()
            .include_gasoline_hybrids()
            .include_gasoline()
            .include_diesel_hybrids()
            .with_min_doors(4)
            .with_max_doors(4)
            .with_max_mileage(50000)
            .with_driving_wheel_heating()
            .include_electric_engines())


def fetch_car_offerings_impl(
        redis_host: str,
        redis_port: int,
        namespace: str,
        every_minutes: int,
        bot: SyncBot,
        telegram_channel_id: int,
):
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    repo = CarsRepository.create(redis_client, namespare=namespace)
    request_builder = get_used_bmw_searcher()
    _report_on_launch(
        telegram_channel_id=telegram_channel_id,
        bot=bot,
        request_builder=request_builder
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
            'message': ('Daily check: BMW crawler bot is still up and running. '
                        f'Using query:\n\n{request_builder.pretty_str()}'),
        },
    )
    scheduler.start()
