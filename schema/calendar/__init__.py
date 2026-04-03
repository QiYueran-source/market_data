'''
交易日历库

表:  
- akshare_trade_calendar: 用akshare获取交易日历数据 

schema:  
- AKSHARE_TRADE_CALENDAR_SCHEMA: 用akshare获取交易日历数据的schema
- STOCKAPI_TRADE_CALENDAR_SCHEMA: 用stock_api获取交易日历数据的schema
'''
from schema.calendar._akshare import AKSHARE_TRADE_CALENDAR_SCHEMA
from schema.calendar.stock_api import STOCKAPI_TRADE_CALENDAR_SCHEMA

__all__ = ['AKSHARE_TRADE_CALENDAR_SCHEMA', 'STOCKAPI_TRADE_CALENDAR_SCHEMA']