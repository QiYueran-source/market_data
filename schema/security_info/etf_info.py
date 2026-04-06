'''
etf_info表的schema
'''
import numpy as np
from utils.schema import col, TableSchema

ETF_INFO_SCHEMA = TableSchema(
    database_name='security_info.db',
    table_name='etf_info',
    schema=[
        col('code', np.str_, 'TEXT', None, True),
        col('name', np.str_, 'TEXT', '未知ETF', False),
        col('exchange', np.str_, 'TEXT', '未知交易所', False),
        col('last_update_date', np.str_, 'TEXT', '2026-04-06', False),
    ]
)