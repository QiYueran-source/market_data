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
DB_NAME = 'daily_trade_data.db'
TABLE_NAME = 'etf_daily_trade_data'

# 列
COLUMNS_LITERAL = Literal['trade_date', 'code', 'yesterday_close_price', 'open', 'high', 'low', 'close', 'volume', 'amount', 'up_down', 'up_down_rate', 'turnover_rate', 'amplitude', 'original_volume', 'pe_ratio']

def get_etf_daily_trade_data(
    codes:str |List[str],
    start_date:str | dt.date = dt.date(2020, 1, 1),
    end_date:str | dt.date = dt.date.today(),
    columns:List[COLUMNS_LITERAL] | 'all' = 'all'
)->pd.DataFrame:
    '''
    获取ETF日线交易数据

    - 参数
        - codes: str | List[str] ETF代码(列表)
        - start_date: str | dt.date 开始日期
        - end_date: str | dt.date 结束日期
        - columns: List[COLUMNS_LITERAL] | 'all' 列名，'all'表示所有列

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
    # 日期参数
    if isinstance(start_date, str):
        start_date = dt.date.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = dt.date.strptime(end_date, '%Y-%m-%d')
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')
    start_datetime = dt.datetime.combine(start_date, dt.time(0, 0, 0))
    end_datetime = dt.datetime.combine(end_date, dt.time(23, 59, 59))
    # 列参数
    if columns == 'all':
        columns = '*'
    else:
        columns_set = set(columns)
        columns = ','.join(columns_set)
    
    query = f'SELECT {columns} FROM etf_daily_trade_data WHERE code IN ({",".join(["?" for _ in codes])}) AND trade_date BETWEEN ? AND ?'
    params = tuple(codes) + (start_datetime, end_datetime)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df