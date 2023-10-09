import asyncio
import pathlib
import re
import tempfile
from collections.abc import Sequence
from typing import Literal, Self

import requests
from loguru import logger
from telethon import TelegramClient
from telethon.hints import FileLike


class SyncBot:
    def __init__(self, client: TelegramClient, event_loop: asyncio.AbstractEventLoop):
        self.event_loop = event_loop
        self.client = client

    @classmethod
    def from_bot_token(cls, api_id: int, api_hash: str, bot_token: str) -> Self:
        event_loop = asyncio.get_event_loop()
        client = TelegramClient(
            api_id=api_id, api_hash=api_hash, session='otodom'
        ).start(bot_token=bot_token)

        return cls(client=client, event_loop=event_loop)

    def send_message(
        self, chat_id: int | str, text: str, parse_mode: Literal['md', 'html']
    ):
        return self.event_loop.run_until_complete(
            self.client.send_message(
                entity=chat_id, message=text, parse_mode=parse_mode
            )
        )

    def send_document(self, chat_id: int | str, document: FileLike):
        return self.event_loop.run_until_complete(
            self.client.send_file(entity=chat_id, file=document, force_document=True)
        )

    def send_photo(self, chat_id: int | str, photo: FileLike | Sequence[FileLike]):
        return self.event_loop.run_until_complete(
            self.client.send_file(entity=chat_id, file=photo, force_document=False)
        )

    def send_photo_from_url(self, chat_id: int | str, photo_url: str | Sequence[str]):
        photo_urls = [photo_url] if isinstance(photo_url, str) else list(photo_url)

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for idx, photo_url in enumerate(photo_urls):
                with (
                    requests.get(photo_url, stream=True, timeout=15) as r,
                    (path := pathlib.Path(tmpdir) / f'image_{idx}.jpg').open('wb') as f,
                ):
                    r.raise_for_status()
                    logger.info('Downloading {} to {}', photo_url, str(path.absolute()))
                    f.write(r.content)
                    paths.append(path.absolute())

            self.send_photo(chat_id, photo=paths)


def escape_markdown(text: str, version: int = 1, entity_type: str | None = None) -> str:
    if int(version) == 1:
        escape_chars = r'_*`['
    elif int(version) == 2:
        if entity_type in ['pre', 'code']:
            escape_chars = r'\`'
        elif entity_type in ['text_link', 'custom_emoji']:
            escape_chars = r'\)'
        else:
            escape_chars = r'\_*[]()~`>#+-=|{}.!'
    else:
        raise ValueError('Markdown version must be either 1 or 2!')

    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
