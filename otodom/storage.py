import pathlib
import sqlite3
import textwrap
from datetime import datetime
from typing import NamedTuple

from otodom.models import Flat, FlatList
from otodom.util import dt_to_naive_utc

FLATS_TABLE = "flats"


class StorageContext(NamedTuple):
    sqlite_conn: sqlite3.Connection
    sqlite_path: pathlib.Path
    raw_json_path: pathlib.Path


class NewAndUpdateFlats(NamedTuple):
    new_flats: list[Flat]
    updated_flats: list[Flat]


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
            url text not null,
            found_ts text,
            title text,
            picture_url text,
            summary_location text,
            price INTEGER,
            updated_at text,
            filter_name text not null,
            PRIMARY KEY (url, filter_name)
        )
        """
        )
    return StorageContext(
        sqlite_conn=conn, raw_json_path=raw_json_path, sqlite_path=sqlite_db_path
    )


def filter_new_flats(
    conn: sqlite3.Connection, flats: list[Flat], filter_name: str
) -> NewAndUpdateFlats:
    cur = conn.cursor()
    urls = [f"""'{f.url}'""" for f in flats]
    urls_in_cond = ",".join(urls)
    res = cur.execute(
        f"""
        SELECT url, updated_at
        FROM {FLATS_TABLE}
        WHERE url IN ({urls_in_cond}) AND filter_name = ?
    """,
        [filter_name],
    )
    url_to_item = {t[0]: t for t in res}

    new_flats = [f for f in flats if f.url not in url_to_item]
    updated_flats = [
        f
        for f in flats
        if f.url in url_to_item
        and f.updated_ts > datetime.fromisoformat(url_to_item[f.url][1])
    ]

    return NewAndUpdateFlats(new_flats=new_flats, updated_flats=updated_flats)


def get_total_flats_in_db(conn: sqlite3.Connection, filter_name: str):
    cur = conn.cursor()
    res = cur.execute(
        f"""
        SELECT COUNT(*) FROM {FLATS_TABLE} 
        WHERE filter_name = ?
    """,
        [filter_name],
    )
    return res.fetchone()[0]


def _insert_flats_unsafe(cur: sqlite3.Cursor, flats: list[Flat], filter_name: str):
    cur.executemany(
        f"""
        INSERT INTO {FLATS_TABLE} VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                f.url,
                f.found_ts.isoformat(),
                f.title,
                f.picture_url,
                f.summary_location,
                f.price,
                dt_to_naive_utc(f.updated_ts).isoformat(),
                filter_name,
            )
            for f in flats
        ),
    )


def insert_flats(conn: sqlite3.Connection, flats: list[Flat], filter_name: str):
    cur = conn.cursor()
    _insert_flats_unsafe(cur, flats, filter_name)
    conn.commit()


def update_flats(conn: sqlite3.Connection, flats: list[Flat], filter_name: str):
    cur = conn.cursor()
    urls_in_cond = ",".join([f"'{f.url}'" for f in flats])
    sql = textwrap.dedent(
        f"""\
        DELETE FROM {FLATS_TABLE}
        WHERE url IN ({urls_in_cond}) AND filter_name = '{filter_name}'
    """
    )
    cur.execute(sql)
    _insert_flats_unsafe(cur, flats, filter_name)
    conn.commit()


def dump_fetched_flats(
    flats: list[Flat], filter_name: str, storage_context: StorageContext, now: datetime
):
    flat_list = FlatList(flats=flats)
    dir = storage_context.raw_json_path / f"filter={filter_name}"
    dir.mkdir(exist_ok=True)
    with (dir / f"fetched_flat_list_{now.timestamp()}.json").open("w") as f:
        f.write(flat_list.json())


def dump_new_flats(
    flats: list[Flat], filter_name: str, storage_context: StorageContext, now: datetime
):
    dir = storage_context.raw_json_path / f"filter={filter_name}"
    dir.mkdir(exist_ok=True)
    with (dir / f"new_flat_list_{now.timestamp()}.json").open("w") as f:
        f.write(FlatList(flats=flats).json())


def dump_updated_flats(
    flats: list[Flat], filter_name: str, storage_context: StorageContext, now: datetime
):
    dir = storage_context.raw_json_path / f"filter={filter_name}"
    dir.mkdir(exist_ok=True)
    with (dir / f"updated_flat_list_{now.timestamp()}.json").open("w") as f:
        f.write(FlatList(flats=flats).json())
