import textwrap

from otodom.cars.model import CarOffering, DealerMetadata
from otodom.report import CANONICAL_CHANNEL_IDS
from otodom.telegram_sync import SyncBot


def report_offering(
    offering: CarOffering,
    dealer: DealerMetadata | None,
    fact_message: str,
    bot: SyncBot,
    telegram_channel_id: str,
):
    telegram_channel_id = CANONICAL_CHANNEL_IDS[telegram_channel_id]
    bot.send_message(
        telegram_channel_id,
        textwrap.dedent(
            f'''\
        **{fact_message}** offering.

        **Model**: {offering.model_name}
        **Engine type**: {offering.electrification_type}
        **Cost**: {offering.gross_sales_price} {offering.currency}

        [Link]({offering.get_url()})
        Last update of offering at: {offering.system_updated_at}
        '''
        ),
        parse_mode='md',
    )
    bot.send_photo_from_url(telegram_channel_id, offering.image_urls[1:4])
