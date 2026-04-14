'''
用stock_api获取交易日历数据  
- get_trade_calendar() 获取一个范围内的交易日历  
- get_trade_calendar_by_date() 获取一个日期的交易日历数据  
- is_trade_date() 判断一个日期是不是交易日
'''
# 库
import os
import datetime as dt
import pandas as pd
import sqlite3

# 数据库常量
from db import DB_DIR
DB_NAME = 'trade_calendar.db'
TABLE_NAME = 'stock_api_trade_calendar'

# 兜底
FALLBACK_IS_OPEN = -1

def get_trade_calendar(
    start_date: dt.date | str = '1990-01-01', 
    end_date: dt.date | str = '2024-12-31',
) -> pd.DataFrame:
    '''
    获取交易日历数据

    参数：
    - start_date: 起始日期，格式为yyyy-mm-dd，默认1990-01-01
    - end_date: 结束日期，格式为yyyy-mm-dd，默认2024-12-31

    返回：
    - pandas.DataFrame: 交易日历数据  
        - calendar_date : str 日期   
        - is_open : 0表示非交易日，1表示交易日
    '''
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, '%Y-%m-%d').date()
    if start_date > end_date:
        raise ValueError('起始日期不能大于结束日期')
    query = f'''
        SELECT * FROM {TABLE_NAME} WHERE calendar_date BETWEEN '{start_date}' AND '{end_date}'
    '''
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    return df

def get_trade_calendar_by_date(
    date: dt.date | str,
) -> pd.DataFrame:
    '''
    获取指定日期的交易日历数据

    参数：
    - date: 日期，格式为yyyy-mm-dd

    返回：
    - pandas.DataFrame: 交易日历数据  
        - calendar_date : str 日期   
        - is_open : 0表示非交易日，1表示交易日, -1兜底，认为是非交易日
    '''
    if isinstance(date, str):
        date = dt.datetime.strptime(date, '%Y-%m-%d').date()
    query = f'''
        SELECT * FROM {TABLE_NAME} WHERE calendar_date = '{date}'    '''
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    return df

def is_trade_date(
    date: dt.date | str,
) -> bool:
    '''
    判断指定日期是否为交易日   
    如果查询结果为-1，则认为是非交易日

    参数：
    - date: 日期，格式为yyyy-mm-dd

    返回：
    - bool: 是否为交易日
    '''
    if isinstance(date, str):
        date = dt.datetime.strptime(date, '%Y-%m-%d').date()
    query = f'''
        SELECT is_open FROM {TABLE_NAME} WHERE calendar_date = '{date}'
    '''
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    if df.empty:
        return False
    return df['is_open'].iloc[0] == 1