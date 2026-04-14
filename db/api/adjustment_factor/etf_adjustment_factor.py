'''
ETF复权因子API接口 

- get_etf_adjustment_factor(): 获取ETF复权因子
'''
# 库
import os
import sqlite3
import datetime as dt
import pandas as pd
from typing import List, Literal

# 工具
from db.api.security_info import etf_info

# 常量
from db import DB_DIR
DB_NAME = 'adjustment_factor.db'
TABLE_NAME = 'etf_adjustment_factor'
ETF_LIST = etf_info.get_etf_list()

# 列
COLUMNS_LITERAL = Literal['code', 'trade_date', 'pre_adjustment_factor', 'post_adjustment_factor']
ALL_COLUMNS = ('code', 'trade_date', 'pre_adjustment_factor', 'post_adjustment_factor')

def get_etf_adjustment_factor(
    codes:str | List[str],
    start_date:str | dt.date = dt.date(2020, 1, 1),
    end_date:str | dt.date = dt.date.today(),
    columns:List[COLUMNS_LITERAL] | Literal['all'] = 'all'
)->pd.DataFrame:
    '''
    获取ETF复权因子
    '''
    # 代码参数
    if isinstance(codes, str):
        codes = [codes]
    if not codes:
        raise ValueError('codes不能为空')
    if not all(code in ETF_LIST for code in codes):
        missing_codes = [code for code in codes if code not in ETF_LIST]
        raise ValueError(f'codes: {missing_codes} 不在ETF列表中')
        
    # 日期参数
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, '%Y-%m-%d').date()
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')

    # 列参数
    if columns == 'all':
        selected_columns = '*'
    else:
        if not columns:
            raise ValueError('columns不能为空')
        invalid_columns = [col for col in columns if col not in ALL_COLUMNS]
        if invalid_columns:
            raise ValueError(f'columns: {invalid_columns} 非法')
        selected_columns = ', '.join(columns)

    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        SELECT {selected_columns}
        FROM {TABLE_NAME}
        WHERE code IN ({placeholders})
        AND trade_date BETWEEN ? AND ?
    '''
    params = tuple(codes) + (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df

