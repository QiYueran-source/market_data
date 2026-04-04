'''
数据库目录  

设置一个DB_SCHEMAS字典，定义为：
{
    数据库名称: [表1, 表2, 表3]
}

DBS_LTERAL: 数据库名称的类型
'''
from typing import Literal
from schema.trade_calendar import TRADE_CALENDAR_SCHEMAS_LIST

# 常量定义
DB_DIR = 'db' # 数据库目录
DB_SCHEMAS = {
    'trade_calendar': TRADE_CALENDAR_SCHEMAS_LIST
} # 表结构列表

__all__ = ['DB_DIR', 'DB_SCHEMAS']