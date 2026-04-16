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
import datetime as dt
import pandas as pd
from typing import List

# 常量
from db.api.security_info import _security_info_db

DB_NAME = _security_info_db.SECURITY_INFO_DB_NAME
TABLE_NAME = 'stock_info'
_SELECT = _security_info_db.SELECT_ALL_COLS

# 兜底股票
FALLBACK_STOCK_CODE = '888888'


def _fb() -> tuple[str]:
    return (FALLBACK_STOCK_CODE,)


def get_all_stock_info() -> pd.DataFrame:
    '''
    获取所有股票信息
    '''
    q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE code != ?'
    return _security_info_db.read_sql(q, _fb())


def get_stock_list() -> List[str]:
    '''
    获取股票列表
    '''
    q = f'SELECT code FROM {TABLE_NAME} WHERE code != ?'
    df = _security_info_db.read_sql(q, _fb())
    return df['code'].tolist()


def get_latest_stock_info() -> pd.DataFrame:
    '''
    获取最新股票信息
    '''
    q = f'''
    SELECT {_SELECT} FROM {TABLE_NAME}
    WHERE last_update_date = (SELECT MAX(last_update_date) FROM {TABLE_NAME})
    AND code != ?
    '''
    return _security_info_db.read_sql(q, _fb())


def get_latest_stock_list() -> List[str]:
    '''
    获取最新股票列表
    '''
    q = f'''
    SELECT code FROM {TABLE_NAME}
    WHERE last_update_date = (SELECT MAX(last_update_date) FROM {TABLE_NAME})
    AND code != ?
    '''
    df = _security_info_db.read_sql(q, _fb())
    return df['code'].tolist()


def get_stock_info_by_code(code: str) -> pd.DataFrame:
    '''
    获取指定代码的股票信息
    '''
    q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE code = ? AND code != ?'
    return _security_info_db.read_sql(q, (code, FALLBACK_STOCK_CODE))


def match_stock_info_by_name(name: str) -> pd.DataFrame:
    '''
    根据名称匹配股票信息
    '''
    q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE name LIKE ? AND code != ?'
    return _security_info_db.read_sql(q, (f'%{name}%', FALLBACK_STOCK_CODE))


def match_stock_info_by_exchange(exchange: str) -> pd.DataFrame:
    '''
    根据交易所匹配股票信息
    '''
    q = f'SELECT {_SELECT} FROM {TABLE_NAME} WHERE exchange = ? AND code != ?'
    return _security_info_db.read_sql(q, (exchange, FALLBACK_STOCK_CODE))


def get_latest_update_date() -> dt.date:
    '''
    获取最新更新日期

    表为空或 MAX(last_update_date) 为 NULL 时抛出 ValueError。
    '''
    raw = _security_info_db.fetch_max_last_update_date(TABLE_NAME)
    if raw is None:
        raise ValueError('stock_info 无有效 last_update_date（表为空或列为 NULL）')
    return dt.datetime.strptime(raw, '%Y-%m-%d').date()
