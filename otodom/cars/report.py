import textwrap

from otodom.cars.model import CarOffering
from otodom.telegram_sync import SyncBot


def report_offering(
    offering: CarOffering,
    fact_message: str,
    bot: SyncBot,
    telegram_channel_id: str,
):
    # The first images is usually some placeholder, we want to avoid it.
    bot.send_photo_from_url(telegram_channel_id, offering.image_urls[1:4])
    bot.send_message(
        telegram_channel_id,
        textwrap.dedent(
            f"""\
        **{fact_message}** offering (photos 👆)

        **Model**: {offering.model_name}
        **Engine type**: {offering.electrification_type}
        **Cost**: {offering.gross_sales_price} {offering.currency}

        [Link]({offering.get_url()})

        Last update of offering at: {offering.system_updated_at}
        """
        ),
        parse_mode='md',
    )
