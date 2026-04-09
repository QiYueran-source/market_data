'''
日线数据库
- ETF_DAILY_TRADE_DATA_SCHEMA: ETF日线数据schema
'''
from schema.daily_trade_data.etf_daily_trade_data import ETF_DAILY_TRADE_DATA_SCHEMA

DAILY_TRADE_DATA_SCHEMAS_LIST = [
    ETF_DAILY_TRADE_DATA_SCHEMA
]

__all__ = [
    'DAILY_TRADE_DATA_SCHEMAS_LIST',
    'ETF_DAILY_TRADE_DATA_SCHEMA'
]