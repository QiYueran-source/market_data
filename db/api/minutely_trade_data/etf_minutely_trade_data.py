'''
ETF分钟线数据API  
- get_etf_table_list(): 获取有分钟线数据的ETF列表
- get_etf_list(): 获取ETF列表
- get_etf_minutely_trade_data(): 获取ETF分钟线数据
'''
# 库
import os 
import datetime as dt
import sqlite3
import pandas as pd
from typing import List, Literal

# 常量
from db import DB_DIR
DB_NAME = 'minutely_trade_data.db'
TABLE_NAME = 'etf_minutely_trade_data'

# etf_minutely_trade_data.exchange 存大写市场码，与库中一致
_ALLOWED_ETF_EXCHANGES = frozenset({'SH', 'SZ'})
_ETF_CODE_START_WITH = frozenset({'51', '159'})

# 列
COLUMNS_LITERAL = Literal['trade_datetime', 'price', 'volume', 'amount', 'original_volume', 'yesterday_close_price', 'up_down', 'up_down_rate', 'amplitude', 'turnover_rate', 'pe_ratio']

def get_etf_table_list():
    '''
    获取有分钟线数据的ETF列表

    - 返回
        - List[str]: ETF表列表
            - str: ETF表名
    '''
    query = f'''
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND 
    ''' + '(' + ' OR '.join([f'name LIKE ?' for _ in _ETF_CODE_START_WITH]) + ')'
    params = tuple(f'minutely_trade_data_{code}%' for code in _ETF_CODE_START_WITH)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df['name'].tolist()

def get_etf_list()->List[str]:
    '''
    获取ETF列表

    - 返回
        - List[str]: ETF列表
            - str: ETF代码
    '''
    etf_table_list = get_etf_table_list()
    return [table.replace('minutely_trade_data_', '') for table in etf_table_list]


def get_etf_minutely_trade_data(
    code:str,
    start_date:str | dt.date = dt.date(1990, 1, 1),
    end_date:str | dt.date = dt.date.today(),
    columns:List[COLUMNS_LITERAL] | 'all' = 'all'
)->pd.DataFrame:
    '''
    获取ETF分钟线数据

    - 参数
        - code: str ETF代码
        - start_datetime: str | dt.date 开始日期 (start_date : 00:00:00)
        - end_datetime: str | dt.date 结束日期 (end_date : 23:59:59)
        - columns: List[COLUMNS_LITERAL] | 'all' 列名，'all'表示所有列

    - 返回
        - pandas.DataFrame: ETF分钟线数据
            - trade_datetime: str 交易时间
            - price: float 交易价格
            - volume: int 交易量
            - amount: float 交易金额
            - original_volume: int 原始交易量
            - yesterday_close_price: float 昨收价
            - up_down: float 相对昨收盘涨跌额
            - up_down_rate: float 相对昨收盘涨跌率
            - amplitude: float 振幅
            - turnover_rate: float 换手率
            - pe_ratio: float 市盈率
    '''
    # 日期参数
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, '%Y-%m-%d')
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
    
    query = f'SELECT {columns} FROM minutely_trade_data_{code} WHERE trade_datetime BETWEEN ? AND ?'
    params = (start_datetime, end_datetime)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df