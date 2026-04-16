'''交易日历表：日期规整与参数化查询（akshare / stock_api 共用）。'''
from __future__ import annotations

import os
import datetime as dt
import sqlite3
from typing import Any

import pandas as pd

from db import DB_DIR

TRADE_CALENDAR_DB_NAME = 'trade_calendar.db'
_SELECT_COLS = 'calendar_date, is_open'


def trade_calendar_db_path() -> str:
    return os.path.join(DB_DIR, TRADE_CALENDAR_DB_NAME)


def as_calendar_date(value: Any) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.datetime.strptime(value, '%Y-%m-%d').date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    raise TypeError(f'不支持的日期类型: {type(value)!r}')


def select_range(table_name: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    if start > end:
        raise ValueError('起始日期不能大于结束日期')
    q = f'SELECT {_SELECT_COLS} FROM {table_name} WHERE calendar_date BETWEEN ? AND ?'
    with sqlite3.connect(trade_calendar_db_path()) as conn:
        return pd.read_sql_query(q, conn, params=(start.isoformat(), end.isoformat()))


def select_by_date(table_name: str, d: dt.date) -> pd.DataFrame:
    q = f'SELECT {_SELECT_COLS} FROM {table_name} WHERE calendar_date = ?'
    with sqlite3.connect(trade_calendar_db_path()) as conn:
        return pd.read_sql_query(q, conn, params=(d.isoformat(),))


def fetch_is_open(table_name: str, d: dt.date) -> int | None:
    q = f'SELECT is_open FROM {table_name} WHERE calendar_date = ?'
    with sqlite3.connect(trade_calendar_db_path()) as conn:
        row = conn.execute(q, (d.isoformat(),)).fetchone()
    if row is None:
        return None
    return int(row[0])
