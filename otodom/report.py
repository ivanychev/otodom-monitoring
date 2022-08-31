import textwrap
from datetime import datetime
from time import sleep

from telegram import Bot, ParseMode
from telegram.utils.helpers import escape_markdown

from otodom.models import Flat

CHANNEL_ID = -1001527642537


def _compose_report(flat: Flat):
    return escape_markdown(
        textwrap.dedent(
            f"""\
    {flat.title}
    
    Location: {flat.summary_location}
    Price: {flat.price}
    [Link]({flat.url})
    """
        ),
        version=2,
    )


def report_new_flats(
    flats: list[Flat], total_flats: int, bot_token: str, now: datetime
):
    bot = Bot(token=bot_token)
    bot.send_message(
        CHANNEL_ID,
        f"Found {len(flats)} new flats at {now.isoformat()}, total flats: {total_flats}",
    )
    for flat in flats:
        bot.send_message(
            CHANNEL_ID,
            _compose_report(flat),
            parse_mode=ParseMode.MARKDOWN_V2,
            timeout=1000,
        )
        if flat.picture_url:
            bot.send_photo(CHANNEL_ID, flat.picture_url, timeout=1000)

        # This is needed in order to throttle the messages stream.
        sleep(5)
