import textwrap
from datetime import datetime

import tenacity
from loguru import logger
from telegram import Bot, ParseMode
from telegram.error import RetryAfter
from telegram.utils.helpers import escape_markdown

from otodom.models import Flat

CHANNEL_ID = -1001527642537


def _compose_html_report(flat: Flat, prefix: str):
    report = textwrap.dedent(
        f"""\
    <strong>{flat.title}</strong>
    
    <strong>Location:</strong> {flat.summary_location}
    <strong>Price:</strong>  {flat.price}
    
    <a href="{flat.url}">Link</a>
    """
    )

    if prefix:
        report = f"{prefix}\n{report}"
    return report


@tenacity.retry(
    wait=tenacity.wait_exponential(min=15, max=60) + tenacity.wait_random(3, 5),
    stop=tenacity.stop_after_attempt(10),
    retry=tenacity.retry_if_exception_type((RetryAfter,)),
)
def _send_flat_summary(bot: Bot, flat: Flat, prefix: str = ""):
    bot.send_message(
        CHANNEL_ID,
        _compose_html_report(flat, prefix=prefix),
        parse_mode=ParseMode.HTML,
        timeout=1000,
    )
    if flat.picture_url:
        bot.send_photo(CHANNEL_ID, flat.picture_url, timeout=1000)


def report_new_flats(
    flats: list[Flat],
    total_flats: int,
    bot_token: str,
    now: datetime,
    report_on_no_new_flats: bool,
):
    bot = Bot(token=bot_token)
    summary_report = (
        f"Found {len(flats)} new flats at {now.isoformat()}, total flats: {total_flats}"
    )
    logger.info(summary_report)

    if flats or report_on_no_new_flats:
        bot.send_message(
            CHANNEL_ID,
            summary_report,
        )
    for flat in flats:
        _send_flat_summary(bot, flat)
