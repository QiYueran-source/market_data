'''
复权因子库

复权因子都是日线数据  
- etf_adjustment_factor: ETF复权因子  
'''
from schema.adjustment_factor.etf_adjustment_factor import ETF_ADJUSTMENT_FACTOR_SCHEMA

ADJUSTMENT_FACTOR_SCHEMAS_LIST = [
    ETF_ADJUSTMENT_FACTOR_SCHEMA
]

__all__ = [
    'ADJUSTMENT_FACTOR_SCHEMAS_LIST',
    'ETF_ADJUSTMENT_FACTOR_SCHEMA'
]