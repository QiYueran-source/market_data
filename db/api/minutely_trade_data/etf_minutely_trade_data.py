'''
ETF分钟线数据API  
- get_etf_table_list(): 获取有分钟线数据的ETF列表
- get_etf_list(): 获取ETF列表
- get_etf_minutely_trade_data(): 获取ETF分钟线数据
'''
# 库
import os 
import datetime as dt
import sqlite3
import pandas as pd
from typing import List, Literal

# 常量
from db import DB_DIR
from db.api.adjustment_factor import etf_adjustment_factor
DB_NAME = 'minutely_trade_data.db'
TABLE_NAME = 'etf_minutely_trade_data'

# etf_minutely_trade_data.exchange 存大写市场码，与库中一致
_ALLOWED_ETF_EXCHANGES = frozenset({'SH', 'SZ'})
_ETF_CODE_START_WITH = frozenset({'51', '159'})

# 列
COLUMNS_LITERAL = Literal['trade_datetime', 'price', 'volume', 'amount', 'original_volume', 'yesterday_close_price', 'up_down', 'up_down_rate', 'amplitude', 'turnover_rate', 'pe_ratio']
ALL_COLUMNS = (
    'trade_datetime', 'price', 'volume', 'amount', 'original_volume',
    'yesterday_close_price', 'up_down', 'up_down_rate', 'amplitude',
    'turnover_rate', 'pe_ratio'
)
ADJUSTABLE_COLUMNS = ('price', 'yesterday_close_price', 'up_down')

def get_etf_table_list():
    '''
    获取有分钟线数据的ETF列表

    - 返回
        - List[str]: ETF表列表
            - str: ETF表名
    '''
    query = f'''
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND 
    ''' + '(' + ' OR '.join([f'name LIKE ?' for _ in _ETF_CODE_START_WITH]) + ')'
    params = tuple(f'minutely_trade_data_{code}%' for code in _ETF_CODE_START_WITH)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df['name'].tolist()

def get_etf_list()->List[str]:
    '''
    获取ETF列表

    - 返回
        - List[str]: ETF列表
            - str: ETF代码
    '''
    etf_table_list = get_etf_table_list()
    return [table.replace('minutely_trade_data_', '') for table in etf_table_list]


def get_etf_minutely_trade_data(
    code:str,
    start_date:str | dt.date = dt.date(1990, 1, 1),
    end_date:str | dt.date = dt.date.today(),
    columns:List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor:Literal['none', 'pre', 'post'] = 'none'
)->pd.DataFrame:
    '''
    获取ETF分钟线数据

    - 参数
        - code: str ETF代码
        - start_datetime: str | dt.date 开始日期 (start_date : 00:00:00)
        - end_datetime: str | dt.date 结束日期 (end_date : 23:59:59)
        - columns: List[COLUMNS_LITERAL] | 'all' 列名，'all'表示所有列
        - adjustment_factor: Literal['none', 'pre', 'post'] 复权因子，'none'表示不使用复权因子，'pre'表示使用前复权因子，'post'表示使用后复权因子

    - 返回
        - pandas.DataFrame: ETF分钟线数据
            - trade_datetime: str 交易时间
            - price: float 交易价格
            - volume: int 交易量
            - amount: float 交易金额
            - original_volume: int 原始交易量
            - yesterday_close_price: float 昨收价
            - up_down: float 相对昨收盘涨跌额
            - up_down_rate: float 相对昨收盘涨跌率
            - amplitude: float 振幅
            - turnover_rate: float 换手率
            - pe_ratio: float 市盈率
    '''
    # 参数校验
    if not isinstance(code, str) or not code:
        raise ValueError('code不能为空')
    if code not in get_etf_list():
        raise ValueError(f'code: {code} 不在ETF分钟线表列表中')

    # 日期参数
    if isinstance(start_date, str):
        start_date = dt.datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = dt.datetime.strptime(end_date, '%Y-%m-%d').date()
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')
    start_datetime = dt.datetime.combine(start_date, dt.time(0, 0, 0))
    end_datetime = dt.datetime.combine(end_date, dt.time(23, 59, 59))

    # 复权参数
    if adjustment_factor not in ('none', 'pre', 'post'):
        raise ValueError("adjustment_factor必须是'none'、'pre'或'post'")

    # 列参数
    if columns == 'all':
        selected_columns = '*'
    else:
        if not columns:
            raise ValueError('columns不能为空')
        invalid_columns = [col for col in columns if col not in ALL_COLUMNS]
        if invalid_columns:
            raise ValueError(f'columns: {invalid_columns} 非法')
        # 保持列顺序
        selected_columns = ', '.join(columns)

    query = f'''
        SELECT {selected_columns}
        FROM minutely_trade_data_{code}
        WHERE trade_datetime BETWEEN ? AND ?
    '''
    params = (start_datetime, end_datetime)
    with sqlite3.connect(os.path.join(DB_DIR, DB_NAME)) as conn:
        df = pd.read_sql_query(query, conn, params=params)

    if adjustment_factor == 'none' or df.empty:
        return df

    factor_column = (
        'pre_adjustment_factor' if adjustment_factor == 'pre'
        else 'post_adjustment_factor'
    )
    factor_df = etf_adjustment_factor.get_etf_adjustment_factor(
        codes=[code],
        start_date=start_date,
        end_date=end_date,
        columns=['code', 'trade_date', factor_column]
    )
    if factor_df.empty:
        return df

    # trade_datetime -> trade_date 关联复权因子
    df['trade_datetime'] = pd.to_datetime(df['trade_datetime'])
    df['_trade_date'] = df['trade_datetime'].dt.strftime('%Y-%m-%d')
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date']).dt.strftime('%Y-%m-%d')

    merged = df.merge(
        factor_df,
        left_on=['_trade_date'],
        right_on=['trade_date'],
        how='left'
    )
    merged[factor_column] = pd.to_numeric(
        merged[factor_column], errors='coerce'
    ).fillna(1.0)

    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce') * merged[factor_column]

    merged.drop(columns=['trade_date', factor_column, '_trade_date'], inplace=True, errors='ignore')
    merged['trade_datetime'] = merged['trade_datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
    return merged