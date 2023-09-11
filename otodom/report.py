import textwrap
import traceback
from datetime import datetime

import tenacity
from loguru import logger
from telegram import Bot, ParseMode
from telegram.error import RetryAfter
from telegram.utils.helpers import escape_markdown

from otodom.models import Flat

CHANNEL_ID = -1001527642537
TEST_CHANNEL_ID = -1001732967254


def get_channel_id(mode: str):
    if mode == 'dev':
        return TEST_CHANNEL_ID
    if mode == 'prod':
        return CHANNEL_ID
    raise ValueError(f'Unknown mode {mode}')


def _compose_html_report(flat: Flat, prefix: str):
    report = textwrap.dedent(
        f'''\
    <strong>{flat.title}</strong>

    <strong>Location:</strong> {flat.summary_location}
    <strong>Price:</strong>  {flat.price}

    <a href="{flat.url}">Link</a>
    '''
    )

    if prefix:
        report = f'{prefix}\n{report}'
    return report


@tenacity.retry(
    wait=tenacity.wait_exponential(min=15, max=60) + tenacity.wait_random(3, 5),
    stop=tenacity.stop_after_attempt(10),
    retry=tenacity.retry_if_exception_type((RetryAfter,)),
)
def _send_flat_summary(bot: Bot, flat: Flat, mode: str, prefix: str = ''):
    bot.send_message(
        get_channel_id(mode),
        _compose_html_report(flat, prefix=prefix),
        parse_mode=ParseMode.HTML,
        timeout=1000,
    )
    if flat.picture_url:
        bot.send_photo(get_channel_id(mode), flat.picture_url, timeout=1000)


def report_message(bot_token: str, mode: str, message: str, escape: bool = False):
    if escape:
        message = escape_markdown(message, version=2)
    bot = Bot(token=bot_token)
    bot.send_message(
        get_channel_id(mode),
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


def report_error(bot_token: str, mode: str, exception: Exception):
    bot = Bot(token=bot_token)
    tb = ''.join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    tb = escape_markdown(tb, version=2)
    msg = textwrap.dedent(
        f'''\
Error occurred to the bot:

```
{tb}
```

Please check the server\\.
'''
    )
    bot.send_message(
        get_channel_id(mode),
        msg,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


def report_new_flats(
    new_flats: list[Flat],
    updated_flats: list[Flat],
    filter_name: str,
    total_flats: int,
    bot_token: str,
    now: datetime,
    report_on_no_new_flats: bool,
    mode: str,
):
    bot = Bot(token=bot_token)
    summary_report = f'Found {len(new_flats)} new flats, {len(updated_flats)} updated flats for filter #{filter_name} at {now.isoformat()}, total flats: {total_flats}'
    logger.info(summary_report)

    if (new_flats or updated_flats) or report_on_no_new_flats:
        bot.send_message(
            get_channel_id(mode),
            summary_report,
            parse_mode=ParseMode.HTML,
        )
    for flat in new_flats:
        _send_flat_summary(
            bot, flat, mode, prefix=f'Filter: <code>{filter_name}</code>\n<b>NEW</b>'
        )
    for flat in updated_flats:
        _send_flat_summary(
            bot,
            flat,
            mode,
            prefix=f'Filter: #{filter_name}\n<b>UPDATED</b>',
        )
