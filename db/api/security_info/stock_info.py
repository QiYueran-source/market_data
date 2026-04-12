'''
stock_info表的API接口     
- get_all_stock_info() 获取所有股票信息  
- get_stock_list() 获取股票列表  
- get_latest_stock_info() 获取最新股票信息  
- get_latest_stock_list() 获取最新股票列表  
- get_stock_info_by_code() 获取指定代码的股票信息  
- match_stock_info_by_name() 根据名称匹配股票信息  
- match_stock_info_by_exchange() 根据交易所匹配股票信息    
- get_latest_update_date() 获取最新更新日期  
'''
# 库
import os
import datetime as dt
import pandas as pd
import sqlite3
from typing import List, Sequence, Literal

# 常量
from db import DB_DIR
DB_NAME = 'security_info.db'
TABLE_NAME = 'stock_info'

# 兜底股票
FALLBACK_STOCK_CODE = '888888'

def get_all_stock_info()->pd.DataFrame:
    '''
    获取所有股票信息
    '''
    query = f'SELECT * FROM {TABLE_NAME}'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df

def get_stock_list()->List[str]:
    '''
    获取股票列表
    '''
    query = f'SELECT code FROM {TABLE_NAME}'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    return df['code'].tolist()

def get_latest_stock_info()->pd.DataFrame:
    '''
    获取最新股票信息
    '''
    query = f'SELECT * FROM {TABLE_NAME} WHERE last_update_date = (SELECT MAX(last_update_date) FROM {TABLE_NAME})'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df

def get_latest_stock_list()->List[str]:
    '''
    获取最新股票列表
    '''
    query = f'SELECT code FROM {TABLE_NAME} WHERE last_update_date = (SELECT MAX(last_update_date) FROM {TABLE_NAME})'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df['code'].tolist()

def get_stock_info_by_code(code:str)->pd.DataFrame:
    '''
    获取指定代码的股票信息
    '''
    query = f'SELECT * FROM {TABLE_NAME} WHERE code = ?'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=(code,))
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df

def match_stock_info_by_name(name:str)->pd.DataFrame:
    '''
    根据名称匹配股票信息
    '''
    query = f'SELECT * FROM {TABLE_NAME} WHERE name LIKE ?'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=(f'%{name}%',))
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df

def match_stock_info_by_exchange(exchange:str)->pd.DataFrame:
    '''
    根据交易所匹配股票信息
    '''
    query = f'SELECT * FROM {TABLE_NAME} WHERE exchange = ?'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=(exchange,))
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df

def get_stock_info_by_code(code:str)->pd.DataFrame:
    '''
    获取指定代码的股票信息
    '''
    query = f'SELECT * FROM {TABLE_NAME} WHERE code = ?'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=(code,))
    df = df[df['code'] != FALLBACK_STOCK_CODE]
    return df

def get_latest_update_date()->dt.date:
    '''
    获取最新更新日期
    '''
    query = f'SELECT last_update_date FROM {TABLE_NAME} ORDER BY last_update_date DESC LIMIT 1'
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn)
    return dt.datetime.strptime(df['last_update_date'].iloc[0], '%Y-%m-%d').date()