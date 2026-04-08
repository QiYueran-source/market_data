'''
etf_info表的schema
'''
import numpy as np
from models.table_schema import col, TableSchema

ETF_INFO_SCHEMA = TableSchema(
    database_name='security_info.db',
    table_name='etf_info',
    schema=[
        col('code', np.str_, 'TEXT', True),
        col('name', np.str_, 'TEXT', False),
        col('exchange', np.str_, 'TEXT', False),
        col('last_update_date', np.str_, 'TEXT', False),
    ]
)