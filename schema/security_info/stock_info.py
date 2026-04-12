'''
股票列表schema  
'''
from models.table_schema import TableSchema, col
import numpy as np

STOCK_INFO_SCHEMA = TableSchema(
    database_name='security_info.db',
    table_name='stock_info',
    schema=[
        col('code', np.str_, 'TEXT', True),
        col('name', np.str_, 'TEXT', False),
        col('exchange', np.str_, 'TEXT', False),
        col('last_update_date', np.str_, 'TEXT', False),
    ]
)