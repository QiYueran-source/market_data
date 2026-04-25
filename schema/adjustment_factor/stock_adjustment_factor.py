'''
股票复权因子
'''
import numpy as np
from models.table_schema import col, TableSchema

STOCK_ADJUSTMENT_FACTOR_SCHEMA = TableSchema(
    database_name='adjustment_factor.db',
    table_name='stock_adjustment_factor',
    schema=[
        col('code', np.str_, 'TEXT', True),
        col('trade_date', np.str_, 'TEXT', True),
        col('adjustment_factor', np.float64, 'REAL', False),
    ]
)