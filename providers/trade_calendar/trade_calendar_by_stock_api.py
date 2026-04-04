'''
从stock_api获取交易日历数据
'''
# 引入库
import requests
from providers.provider_utils import *  
from schema.trade_calendar import STOCKAPI_TRADE_CALENDAR_SCHEMA

# 获取变量的
STOCKAPI_TRADE_CALENDAR_URL = "https://www.stockapi.com.cn/v1/base/tradeDate"

def fetch():
    response = requests.get(STOCKAPI_TRADE_CALENDAR_URL)
    #return response.json()


