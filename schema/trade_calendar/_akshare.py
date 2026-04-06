'''
用akshare获取交易日历数据

注意：akshare交易数据一次获取所有交易日，因此无需实时更新
'''
import numpy as np
from utils.schema import col, TableSchema

AKSHARE_TRADE_CALENDAR_SCHEMA = TableSchema(
    database_name='trade_calendar.db',
    table_name='akshare_trade_calendar',
    schema=[
        col('calendar_date', np.str_, 'TEXT', True),
        col('is_open', np.int8, 'INTEGER', False)
    ]
)

