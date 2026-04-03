'''
交易日历库

表:  
- akshare_trade_calendar: 用akshare获取交易日历数据 

schema:  
- AKSHARE_TRADE_CALENDAR_SCHEMA: 用akshare获取交易日历数据的schema
- STOCKAPI_TRADE_CALENDAR_SCHEMA: 用stock_api获取交易日历数据的schema

可以使用TRADE_CALENDAR_SCHEMAS_LIST获取包含所有schema的列表
'''
from schema.trade_calendar._akshare import AKSHARE_TRADE_CALENDAR_SCHEMA
from schema.trade_calendar.stock_api import STOCKAPI_TRADE_CALENDAR_SCHEMA

# 包含所有schema的列表
TRADE_CALENDAR_SCHEMAS_LIST = [
    AKSHARE_TRADE_CALENDAR_SCHEMA,
    STOCKAPI_TRADE_CALENDAR_SCHEMA
]

__all__ = [
    'TRADE_CALENDAR_SCHEMAS_LIST', 
    'AKSHARE_TRADE_CALENDAR_SCHEMA', 
    'STOCKAPI_TRADE_CALENDAR_SCHEMA'
]
