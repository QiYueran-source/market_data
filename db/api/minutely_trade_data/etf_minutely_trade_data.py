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
from typing import List, Sequence, Literal

# 常量
from db import DB_DIR
DB_NAME = 'minutely_trade_data.db'
TABLE_NAME = 'etf_minutely_trade_data'

# etf_minutely_trade_data.exchange 存大写市场码，与库中一致
_ALLOWED_ETF_EXCHANGES = frozenset({'SH', 'SZ'})
_ETF_CODE_START_WITH = frozenset({'51', '159'})

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
)->pd.DataFrame:
    '''
    获取ETF分钟线数据

    - 返回
        - pandas.DataFrame: ETF分钟线数据
            - trade_datetime: str 交易时间
            - price: float 交易价格
            - volume: int 交易量
            - amount: float 交易金额
    '''
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, '%Y-%m-%d')
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')
    query = f'SELECT * FROM minutely_trade_data_{code} WHERE trade_datetime BETWEEN ? AND ?'
    params = (start_date, end_date)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df