'''daily_trade_data.db 的通用查询工具（供 ETF/股票日线 API 复用）。'''
from __future__ import annotations

import os
import sqlite3
import datetime as dt
from typing import Sequence

import pandas as pd

from db import DB_DIR

DAILY_TRADE_DATA_DB_NAME = 'daily_trade_data.db'


def daily_trade_data_db_path() -> str:
    return os.path.join(DB_DIR, DAILY_TRADE_DATA_DB_NAME)


def as_date(
    value: str | dt.date | dt.datetime | pd.Timestamp | None,
    *,
    field_name: str,
    default: dt.date | None = None,
) -> dt.date:
    if value is None:
        if default is None:
            raise ValueError(f'{field_name}不能为空')
        return default
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, str):
        return dt.datetime.strptime(value, '%Y-%m-%d').date()
    raise TypeError(f'{field_name}类型不支持: {type(value)}')


def normalize_codes(codes: str | Sequence[str]) -> list[str]:
    if isinstance(codes, str):
        raw = [codes]
    elif isinstance(codes, Sequence):
        raw = [str(code) for code in codes]
    else:
        raise TypeError(f'codes类型不支持: {type(codes)}')

    normalized: list[str] = []
    for code in raw:
        c = code.strip()
        if c:
            normalized.append(c)
    if not normalized:
        raise ValueError('codes不能为空')

    seen: set[str] = set()
    deduplicated: list[str] = []
    for code in normalized:
        if code not in seen:
            seen.add(code)
            deduplicated.append(code)
    return deduplicated


def select_columns(columns: Sequence[str] | str, all_columns: Sequence[str]) -> str:
    if columns == 'all':
        return ', '.join(all_columns)
    if not columns:
        raise ValueError('columns不能为空')
    invalid_columns = [col for col in columns if col not in all_columns]
    if invalid_columns:
        raise ValueError(f'columns: {invalid_columns} 非法')
    return ', '.join(columns)


def read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    with sqlite3.connect(daily_trade_data_db_path()) as conn:
        return pd.read_sql_query(query, conn, params=params)
