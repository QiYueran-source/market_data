'''
缓存模块  
'''
from __future__ import annotations

# 库
import os
import sqlite3
from logging import Logger
from typing import List, Optional

import numpy as np
import pandas as pd

# 工具
from utils.schema import TableSchema, validate

# 常量
from db import DB_DIR

# 异常
from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError

class Buffer:
    def __init__(
        self,
        schema: TableSchema,
        buffer_size: int = 1000,
    ):
        self.schema = schema
        self.buffer_size = buffer_size
        self._cache: List[pd.DataFrame] = []
        self._current_size = 0

    def _df_to_sql_params(self, df: pd.DataFrame, cols: List[str]) -> List[tuple]:
        rows: List[tuple] = []
        for _, row in df[cols].iterrows():
            tup: List[object] = []
            for c in cols:
                v = row[c]
                if pd.isna(v):
                    tup.append(None)
                    continue
                field = self.schema.get_field_by_name(c)
                dt = np.dtype(field.dtype)
                if np.issubdtype(dt, np.datetime64):
                    tup.append(pd.Timestamp(v).strftime('%Y-%m-%d'))
                elif np.issubdtype(dt, np.integer):
                    tup.append(int(v))
                elif np.issubdtype(dt, np.floating):
                    tup.append(float(v))
                else:
                    tup.append(v)
            rows.append(tuple(tup))
        return rows

    def _upsert_df(self, conn: sqlite3.Connection, df: pd.DataFrame) -> None:
        if df.empty:
            return
        pk = self.schema.primary_key
        if not self.schema.primary_key_required or not pk:
            raise ValueError('upsert 需要 TableSchema.primary_key')

        cols = list(df.columns)
        for p in pk:
            if p not in cols:
                raise ValueError(f'upsert 的 df 缺少主键列: {p}')

        non_pk = [c for c in cols if c not in set(pk)]
        table = self.schema.table_name
        col_sql = ', '.join(cols)
        placeholders = ', '.join(['?'] * len(cols))
        pk_sql = ', '.join(pk)
        quoted = f'"{table}"'

        if non_pk:
            set_sql = ', '.join(f'{c} = excluded.{c}' for c in non_pk)
            sql = (
                f'INSERT INTO {quoted} ({col_sql}) VALUES ({placeholders}) '
                f'ON CONFLICT ({pk_sql}) DO UPDATE SET {set_sql}'
            )
        else:
            sql = (
                f'INSERT INTO {quoted} ({col_sql}) VALUES ({placeholders}) '
                f'ON CONFLICT ({pk_sql}) DO NOTHING'
            )

        rows = self._df_to_sql_params(df, cols)
        conn.executemany(sql, rows)

    def flush(self) -> None:
        '''将缓存中的各 DataFrame 依次 upsert 写入数据库，然后清空缓存。'''
        if not self._cache:
            return
        db_path = os.path.join(DB_DIR, self.schema.database_name)
        try:
            with sqlite3.connect(db_path) as conn:
                for df in self._cache:
                    self._upsert_df(conn, df)
                self._cache.clear()
                self._current_size = 0
        except Exception as e:
            raise BufferWriteError(f'写入数据库失败: {e}') from e
        

    def append(self, df: pd.DataFrame) -> bool:
        '''
        添加数据到缓存

        需要校验 df 是否符合 schema

        校验成功后，添加进缓存，并更新缓存大小
        如果缓存大小大于等于缓存大小，则清空缓存，并写入数据库
        '''
        try:
            validate(df, self.schema)
        except ValidError as e:
            raise ValidError(f'缓存校验失败: {e}') from e

        self._cache.append(df.copy())
        self._current_size += len(df)

        if self._current_size >= self.buffer_size:
            self.flush()
        return True
