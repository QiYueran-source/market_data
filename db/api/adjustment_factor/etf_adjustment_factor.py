'''
ETF复权因子API接口 

- get_etf_adjustment_factor(): 获取ETF复权因子
'''
# 库
import datetime as dt
import pandas as pd
from typing import List, Literal

# 工具
from db.api.security_info import etf_info
from db.api.adjustment_factor import _adjustment_factor_query

# 常量
DB_NAME = _adjustment_factor_query.ADJUSTMENT_FACTOR_DB_NAME
TABLE_NAME = 'etf_adjustment_factor'

# 列
COLUMNS_LITERAL = Literal['code', 'trade_date', 'pre_adjustment_factor', 'post_adjustment_factor']
ALL_COLUMNS = ('code', 'trade_date', 'pre_adjustment_factor', 'post_adjustment_factor')

def _get_etf_code_set() -> set[str]:
    return set(etf_info.get_etf_list())

def get_etf_adjustment_factor(
    codes: str | List[str],
    start_date: str | dt.date | dt.datetime | pd.Timestamp = dt.date(2020, 1, 1),
    end_date: str | dt.date | dt.datetime | pd.Timestamp | None = None,
    columns: List[COLUMNS_LITERAL] | Literal['all'] = 'all'
)->pd.DataFrame:
    '''
    获取ETF复权因子
    '''
    # 代码参数
    codes = _adjustment_factor_query.normalize_codes(codes)
    etf_code_set = _get_etf_code_set()
    if not all(code in etf_code_set for code in codes):
        missing_codes = [code for code in codes if code not in etf_code_set]
        raise ValueError(f'codes: {missing_codes} 不在ETF列表中')
        
    # 日期参数
    start_date = _adjustment_factor_query.as_date(start_date, field_name='start_date')
    end_date = _adjustment_factor_query.as_date(
        end_date,
        field_name='end_date',
        default=dt.date.today(),
    )
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')

    # 列参数
    if columns == 'all':
        selected_columns = ', '.join(ALL_COLUMNS)
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
        ORDER BY code, trade_date
    '''
    params = tuple(codes) + (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    return _adjustment_factor_query.read_sql(query, params)

def get_latest_etf_adjustment_factor(
    codes: str | List[str],
    columns: List[COLUMNS_LITERAL] | Literal['all'] = 'all'
) -> pd.DataFrame:
    '''
    获取最新ETF复权因子
    '''
    # 代码参数
    codes = _adjustment_factor_query.normalize_codes(codes)
    etf_code_set = _get_etf_code_set()
    if not all(code in etf_code_set for code in codes):
        missing_codes = [code for code in codes if code not in etf_code_set]
        raise ValueError(f'codes: {missing_codes} 不在ETF列表中')

    # 列参数
    if columns == 'all':
        cols = list(ALL_COLUMNS)
    else:
        if not columns:
            raise ValueError('columns不能为空')
        invalid_columns = [col for col in columns if col not in ALL_COLUMNS]
        if invalid_columns:
            raise ValueError(f'columns: {invalid_columns} 非法')
        cols = list(columns)

    selected_columns = ', '.join([f't.{c}' for c in cols])
    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        WITH latest AS (
            SELECT code, MAX(trade_date) AS max_trade_date
            FROM {TABLE_NAME}
            WHERE code IN ({placeholders})
            GROUP BY code
        )
        SELECT {selected_columns}
        FROM {TABLE_NAME} t
        INNER JOIN latest l
            ON t.code = l.code
            AND t.trade_date = l.max_trade_date
        ORDER BY t.code, t.trade_date
    '''
    params = tuple(codes)
    return _adjustment_factor_query.read_sql(query, params)
    