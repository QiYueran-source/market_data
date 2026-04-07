'''
分钟交易数据库  

由于分钟交易数据量较大，设定为 每个证券对应一个表，
命名为 minutely_trade_data_<code>  

本文件可以定义多个schema，用于不同的证券 
'''
from schema.minutely_trade_data.etf_minutely_trade_data import MINUTELY_TRADE_DATA_518800

# 包含所有schema的列表
MINUTELY_TRADE_DATA_SCHEMAS_LIST = [
    MINUTELY_TRADE_DATA_518800
]

MINUTELY_TRADE_ETF_CODE_LIST = [s.table_name.split('_')[-1] for s in MINUTELY_TRADE_DATA_SCHEMAS_LIST]

__all__ = [
    'MINUTELY_TRADE_DATA_SCHEMAS_LIST',
    'MINUTELY_TRADE_ETF_CODE_LIST',
    'MINUTELY_TRADE_DATA_518800',
]