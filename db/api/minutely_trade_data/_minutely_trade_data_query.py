'''minutely_trade_data.db 的通用查询工具（供 ETF/股票分钟线 API 复用）。

与 daily_trade_data_query.py 保持一致风格。
'''
from __future__ import annotations

import os
import sqlite3
import datetime as dt
from typing import Sequence

import pandas as pd

from db import DB_DIR

MINUTELY_TRADE_DATA_DB_NAME = 'minutely_trade_data.db'


def minutely_trade_data_db_path() -> str:
    return os.path.join(DB_DIR, MINUTELY_TRADE_DATA_DB_NAME)


def as_date(
    value: str | dt.date | dt.datetime | pd.Timestamp | None,
    *,
    field_name: str,
    default: dt.date | None = None,
) -> dt.date:
    """将输入转换为 date 对象（与 daily_trade_data_query 保持一致）。"""
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


def as_datetime(
    value: str | dt.date | dt.datetime | pd.Timestamp | None,
    *,
    field_name: str,
    default_time: dt.time | None = None,
) -> dt.datetime:
    """将输入转换为 datetime 对象（分钟线专用）。"""
    if value is None:
        raise ValueError(f'{field_name}不能为空')
    
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        if default_time is None:
            default_time = dt.time(0, 0, 0)
        return dt.datetime.combine(value, default_time)
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, str):
        # 支持 'YYYY-MM-DD' 或完整 datetime 字符串
        try:
            return dt.datetime.fromisoformat(value.replace(' ', 'T'))
        except ValueError:
            date = dt.datetime.strptime(value, '%Y-%m-%d').date()
            if default_time is None:
                default_time = dt.time(0, 0, 0)
            return dt.datetime.combine(date, default_time)
    raise TypeError(f'{field_name}类型不支持: {type(value)}')


def normalize_codes(codes: str | Sequence[str]) -> list[str]:
    """标准化代码列表（保持与 daily 一致）。"""
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
    """选择列（与 daily_trade_data_query 完全一致）。"""
    if columns == 'all':
        return ', '.join(all_columns)
    if not columns:
        raise ValueError('columns不能为空')
    invalid_columns = [col for col in columns if col not in all_columns]
    if invalid_columns:
        raise ValueError(f'columns: {invalid_columns} 非法')
    return ', '.join(columns)


def read_sql(query: str, params: tuple[object, ...] | None = None) -> pd.DataFrame:
    """统一读取分钟线数据库。"""
    with sqlite3.connect(minutely_trade_data_db_path()) as conn:
        if params is None:
            params = ()
        return pd.read_sql_query(query, conn, params=params)
