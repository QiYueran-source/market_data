'''security_info.db：路径与只读查询封装（etf_info / stock_info 共用）。'''
from __future__ import annotations

import os
import sqlite3
from typing import Any

import pandas as pd

from db import DB_DIR

SECURITY_INFO_DB_NAME = 'security_info.db'

# 与 schema/security_info 中 etf_info / stock_info 列一致
SELECT_ALL_COLS = 'code, name, exchange, last_update_date'


def security_info_db_path() -> str:
    return os.path.join(DB_DIR, SECURITY_INFO_DB_NAME)


def read_sql(query: str, params: tuple[Any, ...] | list[Any] | None = None) -> pd.DataFrame:
    with sqlite3.connect(security_info_db_path()) as conn:
        if params is None:
            return pd.read_sql_query(query, conn)
        return pd.read_sql_query(query, conn, params=params)


def fetch_max_last_update_date(table_name: str) -> str | None:
    row = None
    with sqlite3.connect(security_info_db_path()) as conn:
        row = conn.execute(
            f'SELECT MAX(last_update_date) FROM {table_name}',
        ).fetchone()
    if row is None:
        return None
    return row[0]
