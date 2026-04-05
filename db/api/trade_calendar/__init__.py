'''
交易日历接口  
- akshare_trade_calendar : 用akshare获取交易日历数据  
- stock_api_trade_calendar : 用stock_api获取交易日历数据  
'''
from db.api.trade_calendar import akshare_trade_calendar
from db.api.trade_calendar import stock_api_trade_calendar

__all__ = [
    'akshare_trade_calendar',
    'stock_api_trade_calendar'
]