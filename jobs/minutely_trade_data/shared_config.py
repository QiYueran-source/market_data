'''
分钟交易数据共享配置  

由于分早盘和午盘两个脚本，除了时间外，其他配置都相同，所以抽离出来共享

按照证券类型来划分共享配置

- ETF  
    - 提供者  
        - etf_minutely_trade_data_by_mairui.provide(codes:List)

    - ETF代码列表
        - ETF_CODE_LIST code列表  
        - ETF_CODE_SCHEMA_MAP code:schema映射

    - 缓存
        - ETF_BUFFER_MAP code:buffer映射



- 股票  



- 条件
- CONDITION: 是否是交易日（交易日才更新）  
'''
# 库
import datetime as dt
from storage.buffer import Buffer
from db.api.trade_calendar import stock_api_trade_calendar

# ETF 
## 提供者
from providers.minutely_trade_data import etf_minutely_trade_data_by_mairui

## 证券代码-Schema映射
from schema.minutely_trade_data import ETF_CODE_SCHEMA_MAP
ETF_CODE_LIST = list(ETF_CODE_SCHEMA_MAP.keys())

## 缓存
ETF_BUFFER_MAP = {
    c: Buffer(schema=s, buffer_size=10) for c,s in ETF_CODE_SCHEMA_MAP.items()
}

# 股票

# 条件
CONDITION = stock_api_trade_calendar.is_trade_date(dt.date.today())
INTERVAL_SECONDS = 60 # 间隔多少秒获取一次数据
MORNING_MARKET_END_TIME = dt.time(hour=11, minute=30) # 上午市场结束时间
AFTERNOON_MARKET_END_TIME = dt.time(hour=15, minute=0) # 下午市场结束时间
