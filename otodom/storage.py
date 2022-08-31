import pathlib
import sqlite3
from datetime import datetime
from typing import NamedTuple

from otodom.models import Flat, FlatList

FLATS_TABLE = "flats"


class StorageContext(NamedTuple):
    sqlite_conn: sqlite3.Connection
    sqlite_path: pathlib.Path
    raw_json_path: pathlib.Path


def init_storage(base_data_path: pathlib.Path) -> StorageContext:
    data_path = base_data_path / "data"
    sqlite_db_path = data_path / "sqlite"
    raw_json_path = data_path / "json"

    sqlite_db_path.mkdir(parents=True, exist_ok=True)
    raw_json_path.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect((sqlite_db_path / "flats.db").absolute())
    cur = conn.cursor()

    res = cur.execute(
        f"""SELECT name FROM sqlite_master WHERE type='table' AND name='{FLATS_TABLE}';"""
    )
    exists = bool(res.fetchone())
    if not exists:
        cur.execute(
            f"""
        CREATE TABLE {FLATS_TABLE} (
            url text primary key,
            found_ts text,
            title text,
            picture_url text,
            summary_location text,
            price INTEGER
        )
        """
        )
    return StorageContext(
        sqlite_conn=conn, raw_json_path=raw_json_path, sqlite_path=sqlite_db_path
    )


def filter_new_flats(conn: sqlite3.Connection, flats: list[Flat]):
    cur = conn.cursor()
    urls = [f"""'{f.url}'""" for f in flats]
    urls_in_cond = ",".join(urls)
    res = cur.execute(
        f"""
        SELECT url
        FROM {FLATS_TABLE}
        WHERE url IN ({urls_in_cond})
    """,
    )
    existing_urls = {t[0] for t in res}
    return [f for f in flats if f.url not in existing_urls]


def get_total_flats_in_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    res = cur.execute(f"""SELECT COUNT(*) FROM {FLATS_TABLE}""")
    return res.fetchone()[0]


def insert_flats(conn: sqlite3.Connection, flats: list[Flat]):
    cur = conn.cursor()
    cur.executemany(
        f"""
    INSERT INTO {FLATS_TABLE} VALUES(?, ?, ?, ?, ?, ?)
    """,
        (
            (
                f.url,
                f.found_ts.isoformat(),
                f.title,
                f.picture_url,
                f.summary_location,
                f.price,
            )
            for f in flats
        ),
    )
    conn.commit()


def dump_fetched_flats(
    flats: list[Flat], storage_context: StorageContext, now: datetime
):
    flat_list = FlatList(flats=flats)
    with (
        storage_context.raw_json_path / f"fetched_flat_list_{now.timestamp()}.json"
    ).open("w") as f:
        f.write(flat_list.json())


def dump_new_flats(flats: list[Flat], storage_context: StorageContext, now: datetime):
    new_flats = filter_new_flats(storage_context.sqlite_conn, flats)
    with (storage_context.raw_json_path / f"new_flat_list_{now.timestamp()}.json").open(
        "w"
    ) as f:
        f.write(FlatList(flats=new_flats).json())
