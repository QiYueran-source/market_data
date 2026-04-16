'''adjustment_factor.db 的通用查询工具（供 etf/stock 复权因子 API 复用）。'''
from __future__ import annotations

import os
import sqlite3
import datetime as dt
from typing import Sequence

import pandas as pd

from db import DB_DIR

ADJUSTMENT_FACTOR_DB_NAME = 'adjustment_factor.db'


def adjustment_factor_db_path() -> str:
    return os.path.join(DB_DIR, ADJUSTMENT_FACTOR_DB_NAME)


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

    # 去重且保持顺序，减少 IN 参数重复
    seen: set[str] = set()
    deduplicated: list[str] = []
    for code in normalized:
        if code not in seen:
            seen.add(code)
            deduplicated.append(code)
    return deduplicated


def read_sql(query: str, params: tuple[object, ...]) -> pd.DataFrame:
    with sqlite3.connect(adjustment_factor_db_path()) as conn:
        return pd.read_sql_query(query, conn, params=params)
