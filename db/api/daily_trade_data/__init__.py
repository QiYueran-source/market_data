'''
日线交易数据API

- etf_daily_trade_data: ETF日线交易数据API
- stock_daily_trade_data: 股票日线交易数据API
'''
from db.api.daily_trade_data import etf_daily_trade_data
from db.api.daily_trade_data import stock_daily_trade_data

__all__ = [
    'etf_daily_trade_data',
    'stock_daily_trade_data',
]