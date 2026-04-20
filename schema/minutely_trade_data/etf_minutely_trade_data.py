'''
etf分钟交易数据  

由于分钟交易数据量较大，设定为 每个证券对应一个表，
命名为 minutely_trade_data_<code>  

本文件可以定义多个schema，用于不同的证券 
'''
# 库
import numpy as np

# 表结构
from models.table_schema import col, TableSchema

# 通用schema模板
SCHEMA_TEMPLATE = [
    # 不需要code字段，用表名区分  
    col('trade_datetime', np.str_, 'TEXT', True),
    col('price', np.float64, 'REAL', False),
    col('volume', np.int64, 'INTEGER', False),
    col('amount', np.float64, 'REAL', False),
    col('original_volume', np.int64, 'INTEGER', False),
    col('yesterday_close_price', np.float64, 'REAL', False),
    col('up_down', np.float64, 'REAL', False),
    col('up_down_rate', np.float64, 'REAL', False),
    col('amplitude', np.float64, 'REAL', False),
    col('turnover_rate', np.float64, 'REAL', False),
    col('pe_ratio', np.float64, 'REAL', False),
]

def get_schema(code:str) -> TableSchema:
    return TableSchema(
        database_name='minutely_trade_data.db',
        table_name=f'minutely_trade_data_{code}',
        schema=SCHEMA_TEMPLATE
    )

# 518800 华夏黄金ETF 
MINUTELY_TRADE_DATA_518800 = get_schema('518800')

# 大盘成长股
MINUTELY_TRADE_DATA_159203 = get_schema('159203')

# 恒生指数ETF 
MINUTELY_TRADE_DATA_159920 = get_schema('159920')


# 证券-Schema映射
ETF_CODE_SCHEMA_MAP = {
    '518800': MINUTELY_TRADE_DATA_518800,
    '159203': MINUTELY_TRADE_DATA_159203,
    '159920': MINUTELY_TRADE_DATA_159920,
}
