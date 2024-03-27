import json
import pathlib
import tempfile
import textwrap
import traceback
from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType

from loguru import logger

from otodom.models import Flat
from otodom.telegram_sync import SyncBot, escape_markdown

CANONICAL_CHANNEL_IDS: Mapping[str, int] = MappingProxyType(
    {
        'test': -1001732967254,
        'main': -1001527642537,
        'commercial': -1001977809072,
        'bmw': -1001679108520,
        'polina': -1002070013905,
        'seizbil': -1002110171791,
    }
)


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
        report = f'{prefix}\n{report}'
    return report


# @tenacity.retry(
#     wait=tenacity.wait_exponential(min=15, max=60) + tenacity.wait_random(3, 5),
#     stop=tenacity.stop_after_attempt(10),
# )
def _send_flat_summary(bot: SyncBot, flat: Flat, telegram_channel_id: int, prefix: str = ''):
    bot.send_message(
        telegram_channel_id,
        _compose_html_report(flat, prefix=prefix),
        parse_mode='html',
    )

    if flat.picture_url:
        bot.send_photo_from_url(telegram_channel_id, flat.picture_url)


def report_message(bot: SyncBot, telegram_channel_id: int, message: str, escape: bool = False):
    if escape:
        message = escape_markdown(message, version=2)
    bot.send_message(
        telegram_channel_id,
        message,
        parse_mode='md',
    )


def report_error(
    bot: SyncBot,
    telegram_channel_id: int,
    exception: Exception,
    context: dict | list | None = None,
    uploaded_context_filename: str = 'context.json',
):
    tb = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    msg = textwrap.dedent(
        f"""\
Error occurred to the bot:

```
{tb}
```

Please check the server\\.
"""
    )
    bot.send_message(
        telegram_channel_id,
        msg,
        parse_mode='md',
    )
    if context is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            context_path = pathlib.Path(tmpdir) / uploaded_context_filename
            context_path.write_text(json.dumps(context, sort_keys=True, indent=2))
            bot.send_document(telegram_channel_id, document=str(context_path))


def report_new_flats(
    new_flats: list[Flat],
    updated_flats: list[Flat],
    filter_name: str,
    total_flats: int,
    bot: SyncBot,
    now: datetime,
    report_on_no_new_flats: bool,
    telegram_channel_id: int,
):
    summary_report = f'Found {len(new_flats)} new flats, {len(updated_flats)} updated flats for filter #{filter_name} at {now.isoformat()}, total flats: {total_flats}'
    logger.info(summary_report)

    if (new_flats or updated_flats) or report_on_no_new_flats:
        bot.send_message(
            telegram_channel_id,
            summary_report,
            parse_mode='html',
        )
    for flat in new_flats:
        _send_flat_summary(
            bot,
            flat,
            telegram_channel_id,
            prefix=f'Filter: <code>{filter_name}</code>\n<b>NEW</b>',
        )
    for flat in updated_flats:
        _send_flat_summary(
            bot,
            flat,
            telegram_channel_id,
            prefix=f'Filter: #{filter_name}\n<b>UPDATED</b>',
        )
