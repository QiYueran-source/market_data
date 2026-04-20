'''
股票日线数据  
''' 

import numpy as np
from models.table_schema import col, TableSchema

STOCK_DAILY_TRADE_DATA_SCHEMA = TableSchema(
    database_name='daily_trade_data.db',
    table_name='stock_daily_trade_data',
    schema=[
        col('code', np.str_, 'TEXT', True),
        col('trade_date', np.str_, 'TEXT', True),
        col('open', np.float64, 'REAL', False),
        col('high', np.float64, 'REAL', False),
        col('low', np.float64, 'REAL', False),
        col('close', np.float64, 'REAL', False),
        col('volume', np.int64, 'INTEGER', False),
        col('amount', np.float64, 'REAL', False),
        col('original_volume', np.int64, 'INTEGER', False),
        col('yesterday_close_price', np.float64, 'REAL', False),
        col('up_down', np.float64, 'REAL', False),
        col('up_down_rate', np.float64, 'REAL', False),
        col('amplitude', np.float64, 'REAL', False),
        col('turnover_rate', np.float64, 'REAL', False),
        col('pe_ratio', np.float64, 'REAL', False)
    ]
)