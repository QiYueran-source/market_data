'''
用stock_api获取股票数据
需要实时更新
'''
import numpy as np
from utils.schema import col, TableSchema

STOCKAPI_TRADE_CALENDAR_SCHEMA = TableSchema(
    database_name='calendar',
    table_name='stock_api_trade_calendar',
    schema=[
        col('cal_date', np.datetime64, 'TEXT', None, '交易日，格式为yyyy-mm-dd；由于sqlite限制，使用字符串类型', True),
        col('is_open', np.int8, 'INTEGER', 0, '是否交易日，1：是，0：否；默认0', False)
    ]
)