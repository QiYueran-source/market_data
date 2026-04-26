'''
提供akshare_trade_calendar表的接口   
- get_trade_calendar() 获取一个范围内的交易日历    
- get_trade_calendar_by_date() 获取一个日期的交易日历数据    
- is_trade_date() 判断一个日期是不是交易日  
- get_trade_date_list() 仅返回交易日  
'''
# 库
import datetime as dt
import pandas as pd

# 内部方法
from db.api.trade_calendar import _calendar_query

# 数据库常量
DB_NAME = _calendar_query.TRADE_CALENDAR_DB_NAME
TABLE_NAME = 'akshare_trade_calendar'


def get_trade_calendar(
    start_date: dt.date | dt.datetime | str | pd.Timestamp = '1990-01-01',
    end_date: dt.date | dt.datetime | str | pd.Timestamp = '2024-12-31',
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
    s = _calendar_query.as_calendar_date(start_date)
    e = _calendar_query.as_calendar_date(end_date)
    return _calendar_query.select_range(TABLE_NAME, s, e)


def get_trade_calendar_by_date(
    date: dt.date | dt.datetime | str | pd.Timestamp,
) -> pd.DataFrame:
    '''
    获取指定日期的交易日历数据

    参数：
    - date: 日期，格式为yyyy-mm-dd

    返回：
    - pandas.DataFrame: 交易日历数据  
        - calendar_date : str 日期   
        - is_open : 0表示非交易日，1表示交易日
    '''
    d = _calendar_query.as_calendar_date(date)
    return _calendar_query.select_by_date(TABLE_NAME, d)


def is_trade_date(
    date: dt.date | dt.datetime | str | pd.Timestamp,
) -> bool:
    '''
    判断指定日期是否为交易日

    参数：
    - date: 日期，格式为yyyy-mm-dd

    返回：
    - bool: 是否为交易日
    '''
    d = _calendar_query.as_calendar_date(date)
    v = _calendar_query.fetch_is_open(TABLE_NAME, d)
    if v is None:
        return False
    return v == 1

def get_trade_date_list(
    start_date: dt.date | dt.datetime | str | pd.Timestamp = '1990-01-01',
    end_date: dt.date | dt.datetime | str | pd.Timestamp = '2024-12-31',
) -> list[dt.date]:
    '''
    获取一个范围内的交易日（仅 is_open == 1）。
    '''
    df = get_trade_calendar(start_date, end_date)
    if df.empty or 'calendar_date' not in df.columns or 'is_open' not in df.columns:
        return []
    open_rows = df.loc[df['is_open'] == 1, 'calendar_date']
    if open_rows.empty:
        return []
    dates = pd.to_datetime(open_rows, errors='coerce').dropna().dt.date
    return dates.tolist()