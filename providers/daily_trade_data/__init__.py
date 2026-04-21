'''
日线数据提供者
'''
from . import etf_daily_trade_data_by_mairui
from . import stock_daily_trade_data_by_tushare

__all__ = [
    'etf_daily_trade_data_by_mairui',
    'stock_daily_trade_data_by_tushare',
]