'''
ETF日线交易数据API  
- get_etf_daily_trade_data(): 获取ETF日线交易数据
'''
# 库
import os 
import datetime as dt
import sqlite3
import pandas as pd
from typing import List, Literal

# 常量
from db import DB_DIR
from db.api.adjustment_factor import etf_adjustment_factor
from db.api.security_info import etf_info
DB_NAME = 'daily_trade_data.db'
TABLE_NAME = 'etf_daily_trade_data'
ETF_LIST = etf_info.get_etf_list()

# 列
COLUMNS_LITERAL = Literal['trade_date', 'code', 'yesterday_close_price', 'open', 'high', 'low', 'close', 'volume', 'amount', 'up_down', 'up_down_rate', 'turnover_rate', 'amplitude', 'original_volume', 'pe_ratio']
ALL_COLUMNS = (
    'trade_date', 'code', 'yesterday_close_price', 'open', 'high', 'low', 'close',
    'volume', 'amount', 'up_down', 'up_down_rate', 'turnover_rate', 'amplitude',
    'original_volume', 'pe_ratio'
)
ADJUSTABLE_COLUMNS = (
    'yesterday_close_price', 'open', 'high', 'low', 'close', 'up_down'
)

def get_etf_daily_trade_data(
    codes:str |List[str],
    start_date:str | dt.date = dt.date(2020, 1, 1),
    end_date:str | dt.date = dt.date.today(),
    columns:List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor:Literal['none', 'pre', 'post'] = 'none'
)->pd.DataFrame:
    '''
    获取ETF日线交易数据

    - 参数
        - codes: str | List[str] ETF代码(列表)
        - start_date: str | dt.date 开始日期
        - end_date: str | dt.date 结束日期
        - columns: List[COLUMNS_LITERAL] | 'all' 列名，'all'表示所有列
        - adjustment_factor: Literal['none', 'pre', 'post'] 复权因子，'none'表示不使用复权因子，'pre'表示使用前复权因子，'post'表示使用后复权因子

    - 返回
        - pandas.DataFrame: ETF日线交易数据
            - trade_date: str 交易日期
            - code: str ETF代码
            - yesterday_close_price: float 昨收价
            - open: float 开盘价
            - high: float 最高价
            - low: float 最低价
            - close: float 收盘价
            - volume: int 成交量
            - amount: float 成交金额
            - up_down: float 相对昨收盘涨跌额
            - up_down_rate: float 相对昨收盘涨跌率
            - turnover_rate: float 换手率
            - amplitude: float 振幅
            - original_volume: int 原始成交量
            - pe_ratio: float 市盈率
    '''
    # 代码参数
    if isinstance(codes, str):
        codes = [codes]
    if not codes:
        raise ValueError('codes不能为空')
    if not all(code in ETF_LIST for code in codes):
        missing_codes = [code for code in codes if code not in ETF_LIST]
        raise ValueError(f'codes: {missing_codes} 不在ETF列表中')

    # 日期参数
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, '%Y-%m-%d').date()
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')
    start_datetime = dt.datetime.combine(start_date, dt.time(0, 0, 0))
    end_datetime = dt.datetime.combine(end_date, dt.time(23, 59, 59))

    # 复权参数
    if adjustment_factor not in ('none', 'pre', 'post'):
        raise ValueError("adjustment_factor必须是'none'、'pre'或'post'")

    # 列参数
    if columns == 'all':
        selected_columns = '*'
    else:
        if not columns:
            raise ValueError('columns不能为空')
        invalid_columns = [col for col in columns if col not in ALL_COLUMNS]
        if invalid_columns:
            raise ValueError(f'columns: {invalid_columns} 非法')
        # 保持用户给定列顺序，避免 set 打乱顺序
        selected_columns = ', '.join(columns)

    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        SELECT {selected_columns}
        FROM {TABLE_NAME}
        WHERE code IN ({placeholders})
        AND trade_date BETWEEN ? AND ?
    '''
    params = tuple(codes) + (start_datetime, end_datetime)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)

    # 无复权或空结果，直接返回
    if adjustment_factor == 'none' or df.empty:
        return df

    factor_column = (
        'pre_adjustment_factor' if adjustment_factor == 'pre'
        else 'post_adjustment_factor'
    )
    factor_df = etf_adjustment_factor.get_etf_adjustment_factor(
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        columns=['code', 'trade_date', factor_column]
    )
    if factor_df.empty:
        return df

    # 统一日期格式后按 code + trade_date 关联复权因子
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date']).dt.strftime('%Y-%m-%d')
    merged = df.merge(
        factor_df,
        on=['code', 'trade_date'],
        how='left'
    )
    merged[factor_column] = pd.to_numeric(
        merged[factor_column], errors='coerce'
    ).fillna(1.0)

    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce') * merged[factor_column]

    merged.drop(columns=[factor_column], inplace=True)
    df = merged
    return df