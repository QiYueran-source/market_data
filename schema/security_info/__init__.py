'''
证券信息库  

表:  
- etf_info: ETF信息表

schema:  
- ETF_INFO_SCHEMA: ETF信息表的schema
'''
from schema.security_info.etf_info import ETF_INFO_SCHEMA

# 包含所有schema的列表
SECURITY_INFO_SCHEMAS_LIST = [
    ETF_INFO_SCHEMA
]

__all__ = [
    'SECURITY_INFO_SCHEMAS_LIST',
    'ETF_INFO_SCHEMA'
]