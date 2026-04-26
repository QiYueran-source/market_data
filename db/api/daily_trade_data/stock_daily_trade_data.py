'''
股票日线交易数据 API
- get_stock_daily_trade_data(): 获取股票日线交易数据（可选前/后复权，口径与 ETF 日线一致）
- get_latest_stock_daily_trade_data(): 每 code 最新一行；复权时与日线接口同一锚点算法（见参数 adjust_anchor_start_date）
- get_max_trade_dates_for_codes(): 查询各 code 在库中已有最大 trade_date（用于增量拉取）
'''
from __future__ import annotations

import datetime as dt
from typing import List, Literal

import numpy as np
import pandas as pd

from db.api.adjustment_factor import stock_adjustment_factor
from db.api.security_info import stock_info
from . import _daily_trade_data_query

DB_NAME = _daily_trade_data_query.DAILY_TRADE_DATA_DB_NAME
TABLE_NAME = 'stock_daily_trade_data'

COLUMNS_LITERAL = Literal[
    'trade_date',
    'code',
    'yesterday_close_price',
    'open',
    'high',
    'low',
    'close',
    'volume',
    'amount',
    'up_down',
    'up_down_rate',
    'turnover_rate',
    'amplitude',
    'original_volume',
    'pe_ratio',
]
ALL_COLUMNS = (
    'trade_date',
    'code',
    'yesterday_close_price',
    'open',
    'high',
    'low',
    'close',
    'volume',
    'amount',
    'up_down',
    'up_down_rate',
    'turnover_rate',
    'amplitude',
    'original_volume',
    'pe_ratio',
)
ADJUSTABLE_COLUMNS = (
    'yesterday_close_price',
    'open',
    'high',
    'low',
    'close',
    'up_down',
)


def get_max_trade_dates_for_codes(codes: List[str]) -> dict[str, dt.date | None]:
    '''
    查询给定股票代码在 stock_daily_trade_data 中已有的最大 trade_date。
    无记录则不在字典中或值为 None（实现为仅返回查询到的 code）。
    '''
    codes = _daily_trade_data_query.normalize_codes(codes)
    if not codes:
        return {}
    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        SELECT code, MAX(trade_date) AS mx
        FROM {TABLE_NAME}
        WHERE code IN ({placeholders})
        GROUP BY code
    '''
    df = _daily_trade_data_query.read_sql(query, tuple(codes))
    if df.empty:
        return {c: None for c in codes}
    out: dict[str, dt.date | None] = {c: None for c in codes}
    for _, row in df.iterrows():
        raw = row['mx']
        code = str(row['code']).strip()
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            out[code] = None
        else:
            s = str(raw).strip()[:10]
            out[code] = dt.datetime.strptime(s, '%Y-%m-%d').date()
    return out


def get_stock_daily_trade_data(
    codes: str | List[str],
    start_date: str | dt.date | dt.datetime | pd.Timestamp = dt.date(2020, 1, 1),
    end_date: str | dt.date | dt.datetime | pd.Timestamp | None = None,
    columns: List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor: Literal['none', 'pre', 'post'] = 'none',
) -> pd.DataFrame:
    '''
    获取股票日线交易数据。入库为不复权；`adjustment_factor` 非 none 时按本地
    `stock_adjustment_factor` 与 ETF 日线相同锚点比例做前/后复权（缺失因子则价为 NaN）。

    - codes: 股票代码或列表，须在当前 stock_info 列表中
    - start_date / end_date: 日期范围
    - columns: 返回列；'all' 表示全部列
    - adjustment_factor: 'none' | 'pre' | 'post'
    '''
    codes = _daily_trade_data_query.normalize_codes(codes)
    stock_set = set(stock_info.get_stock_list())
    if not all(code in stock_set for code in codes):
        missing_codes = [code for code in codes if code not in stock_set]
        raise ValueError(f'codes: {missing_codes} 不在股票列表中')

    start_date = _daily_trade_data_query.as_date(start_date, field_name='start_date')
    end_date = _daily_trade_data_query.as_date(
        end_date,
        field_name='end_date',
        default=dt.date.today(),
    )
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')

    if adjustment_factor not in ('none', 'pre', 'post'):
        raise ValueError("adjustment_factor必须是'none'、'pre'或'post'")

    internal_columns = (
        list(columns)
        if isinstance(columns, list)
        else (list(ALL_COLUMNS) if columns == 'all' else list(columns))
    )
    if 'code' not in internal_columns:
        internal_columns = ['code'] + internal_columns
    if 'trade_date' not in internal_columns:
        internal_columns = ['trade_date'] + internal_columns

    selected_columns = _daily_trade_data_query.select_columns(internal_columns, ALL_COLUMNS)
    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        SELECT {selected_columns}
        FROM {TABLE_NAME}
        WHERE code IN ({placeholders})
        AND trade_date BETWEEN ? AND ?
        ORDER BY code, trade_date
    '''
    params = tuple(codes) + (
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
    )
    df = _daily_trade_data_query.read_sql(query, params)

    if adjustment_factor == 'none' or df.empty:
        if columns != 'all' and isinstance(columns, list):
            final_cols = [c for c in columns if c in df.columns]
            if final_cols:
                return df[final_cols]
        return df

    factor_column = 'adjustment_factor'
    factor_df = stock_adjustment_factor.get_stock_adjustment_factor(
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        columns=['code', 'trade_date', factor_column],
    )
    if factor_df.empty:
        if columns != 'all' and isinstance(columns, list):
            final_cols = [c for c in columns if c in df.columns]
            if final_cols:
                return df[final_cols]
        return df

    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date']).dt.strftime('%Y-%m-%d')
    merged = df.merge(
        factor_df,
        on=['code', 'trade_date'],
        how='left',
    )
    merged[factor_column] = pd.to_numeric(
        merged[factor_column], errors='coerce'
    )
    factor_sorted = factor_df.sort_values(['code', 'trade_date']).copy()
    factor_sorted[factor_column] = pd.to_numeric(
        factor_sorted[factor_column], errors='coerce'
    )
    anchors = factor_sorted.groupby('code', as_index=False).agg(
        factor_start=(factor_column, 'first'),
        factor_end=(factor_column, 'last'),
    )
    merged = merged.merge(anchors, on='code', how='left')

    ratio_column = '_adjustment_ratio'
    if adjustment_factor == 'pre':
        merged[ratio_column] = merged[factor_column] / merged['factor_end']
    else:
        merged[ratio_column] = merged[factor_column] / merged['factor_start']
    merged[ratio_column] = merged[ratio_column].replace([np.inf, -np.inf], np.nan)

    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')

    mask_has_ratio = merged[ratio_column].notna()
    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged.loc[mask_has_ratio, col] = (
                merged.loc[mask_has_ratio, col] * merged.loc[mask_has_ratio, ratio_column]
            )

    mask_no_ratio = merged[ratio_column].isna()
    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged.loc[mask_no_ratio, col] = np.nan

    merged.drop(
        columns=[factor_column, 'factor_start', 'factor_end', ratio_column],
        inplace=True,
    )
    df = merged

    if columns != 'all' and isinstance(columns, list):
        final_cols = [c for c in columns if c in df.columns]
        if final_cols:
            return df[final_cols]
    return df

def get_latest_stock_daily_trade_data(
    codes: str | List[str] | Literal['all'] = 'all',
    columns: List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor: Literal['none', 'pre', 'post'] = 'none',
    adjust_anchor_start_date: str | dt.date | dt.datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    '''
    获取给定股票代码的最新一条日线交易数据（每个 code 仅一行）。

    - codes: 股票代码、代码列表或 'all'
    - columns: 返回列；'all' 表示全部列
    - adjustment_factor: 'none' 走库内 MAX(trade_date) 单条查询；'pre'/'post' 时拉
      [adjust_anchor_start_date, 今天] 区间日线并复权后按 code 取末行（与 get_stock_daily_trade_data 锚点一致）。
    - adjust_anchor_start_date: 复权区间起点；默认 2010-01-01。'all' + 复权时数据量大，注意内存。
    '''
    if adjustment_factor not in ('none', 'pre', 'post'):
        raise ValueError("adjustment_factor必须是'none'、'pre'或'post'")

    if codes == 'all':
        codes = stock_info.get_stock_list()
    codes = _daily_trade_data_query.normalize_codes(codes)

    stock_set = set(stock_info.get_stock_list())
    if not all(code in stock_set for code in codes):
        missing_codes = [code for code in codes if code not in stock_set]
        raise ValueError(f'codes: {missing_codes} 不在股票列表中')

    if adjustment_factor != 'none':
        anchor = adjust_anchor_start_date
        if anchor is None:
            anchor = dt.date(2010, 1, 1)
        anchor = _daily_trade_data_query.as_date(anchor, field_name='adjust_anchor_start_date')
        wide = get_stock_daily_trade_data(
            codes=codes,
            start_date=anchor,
            end_date=dt.date.today(),
            columns=columns,
            adjustment_factor=adjustment_factor,
        )
        if wide.empty:
            return wide
        wide = wide.sort_values(['code', 'trade_date'], kind='mergesort')
        out = wide.groupby('code', sort=False).tail(1).reset_index(drop=True)
        return out

    internal_columns = (
        list(columns)
        if isinstance(columns, list)
        else (list(ALL_COLUMNS) if columns == 'all' else list(columns))
    )
    if 'code' not in internal_columns:
        internal_columns = ['code'] + internal_columns
    if 'trade_date' not in internal_columns:
        internal_columns = ['trade_date'] + internal_columns

    selected_columns = ', '.join([f't.{col}' for col in internal_columns])
    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        WITH latest AS (
            SELECT code, MAX(trade_date) AS max_trade_date
            FROM {TABLE_NAME}
            WHERE code IN ({placeholders})
            GROUP BY code
        )
        SELECT {selected_columns}
        FROM {TABLE_NAME} t
        INNER JOIN latest l
            ON t.code = l.code
            AND t.trade_date = l.max_trade_date
        ORDER BY t.code, t.trade_date
    '''
    df = _daily_trade_data_query.read_sql(query, tuple(codes))

    if columns != 'all' and isinstance(columns, list):
        final_cols = [c for c in columns if c in df.columns]
        if final_cols:
            return df[final_cols]
    return df