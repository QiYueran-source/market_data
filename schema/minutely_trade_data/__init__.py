'''
分钟交易数据库  

由于分钟交易数据量较大，设定为 每个证券对应一个表，
命名为 minutely_trade_data_<code>  

本文件可以定义多个schema，用于不同的证券   
- ETF_CODE_SCHEMA_MAP: ETF 证券代码-Schema映射  

- MINUTELY_TRADE_DATA_SCHEMAS_LIST: 包含所有schema的列表(包括股票和ETF)
'''
from schema.minutely_trade_data.etf_minutely_trade_data import (
    ETF_CODE_SCHEMA_MAP
)

# 包含所有schema的列表
MINUTELY_TRADE_DATA_SCHEMAS_LIST = [
    *list(ETF_CODE_SCHEMA_MAP.values())
]

__all__ = [
    'MINUTELY_TRADE_DATA_SCHEMAS_LIST',
    'ETF_CODE_SCHEMA_MAP',
]