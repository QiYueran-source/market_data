'''
用stock_api获取股票数据
需要实时更新
'''
import numpy as np
from models.table_schema import col, TableSchema

STOCKAPI_TRADE_CALENDAR_SCHEMA = TableSchema(
    database_name='trade_calendar.db',
    table_name='stock_api_trade_calendar',
    schema=[
        col('calendar_date', np.str_ , 'TEXT', True),
        col('is_open', np.int8, 'INTEGER', False)
    ]
)