'''
ETF分钟线数据API  
- get_etf_table_list(): 获取有分钟线数据的ETF列表
- get_etf_list(): 获取ETF列表
- get_etf_minutely_trade_data(): 获取ETF分钟线数据（复权使用 post_adjustment_factor）

支持ETF：
- 51xxxx (上证)
- 159xxx (深证)
- 15xxxx (恒生指数ETF，如159920)
'''
# 库
import datetime as dt
import pandas as pd
import numpy as np
import sqlite3
from typing import List, Literal

# 工具
from db.api.adjustment_factor import etf_adjustment_factor
from . import _minutely_trade_data_query

# 常量
DB_NAME = _minutely_trade_data_query.MINUTELY_TRADE_DATA_DB_NAME
TABLE_NAME = 'etf_minutely_trade_data'

# etf_minutely_trade_data.exchange 存大写市场码，与库中一致
_ALLOWED_ETF_EXCHANGES = frozenset({'SH', 'SZ'})
_ETF_CODE_START_WITH = frozenset({'51', '159', '15'})

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
        ({' OR '.join([f"name LIKE ?" for _ in _ETF_CODE_START_WITH])})
    '''
    params = tuple(f'minutely_trade_data_{code}%' for code in _ETF_CODE_START_WITH)
    # 使用 query 工具中的 path 函数（避免重复 import sqlite3）
    db_path = _minutely_trade_data_query.minutely_trade_data_db_path()
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df['name'].tolist()


def get_etf_list() -> List[str]:
    '''
    获取ETF列表

    - 返回
        - List[str]: ETF列表
            - str: ETF代码
    '''
    etf_table_list = get_etf_table_list()
    return [table.replace('minutely_trade_data_', '') for table in etf_table_list]


def _apply_adjustment(
    df: pd.DataFrame,
    codes: List[str],
    start_date: dt.date,
    end_date: dt.date,
    adjustable_columns: tuple[str, ...],
) -> pd.DataFrame:
    """应用复权因子（当前使用 post_adjustment_factor，因为数据库中实际存储的是后复权因子）。
    复权因子缺失时保持NaN，不再默认填充1.0。
    """
    if df.empty:
        return df

    factor_column = 'post_adjustment_factor'
    factor_df = etf_adjustment_factor.get_etf_adjustment_factor(
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        columns=['code', 'trade_date', factor_column]
    )
    if factor_df.empty:
        return df

    # 统一日期格式后关联
    df = df.copy()
    df['trade_date'] = pd.to_datetime(df['trade_datetime']).dt.strftime('%Y-%m-%d')
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date']).dt.strftime('%Y-%m-%d')

    merged = df.merge(
        factor_df,
        on=['trade_date'],  # 分钟线不一定有 code 列
        how='left'
    )
    merged[factor_column] = pd.to_numeric(
        merged[factor_column], errors='coerce'
    )
    # 复权因子缺失时，对应的可调整价格字段也设为NaN

    # 先对所有可调整列做数值转换
    for col in adjustable_columns:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')

    # 对有复权因子的行进行调整
    mask_has_factor = merged[factor_column].notna()
    for col in adjustable_columns:
        if col in merged.columns:
            merged.loc[mask_has_factor, col] = (
                merged.loc[mask_has_factor, col] * merged.loc[mask_has_factor, factor_column]
            )

    # 对缺失复权因子的行，将可调整的价格字段设为NaN
    mask_no_factor = merged[factor_column].isna()
    for col in adjustable_columns:
        if col in merged.columns:
            merged.loc[mask_no_factor, col] = np.nan

    merged.drop(columns=[factor_column, 'trade_date'], inplace=True, errors='ignore')
    return merged


def get_etf_minutely_trade_data(
    code: str,
    start_date: str | dt.date = dt.date(1990, 1, 1),
    end_date: str | dt.date = dt.date.today(),
    columns: List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor: Literal['none', 'pre', 'post'] = 'none'
) -> pd.DataFrame:
    '''
    获取ETF分钟线数据

    - 参数
        - code: str ETF代码（单个）
        - start_date: str | dt.date 开始日期 (00:00:00)
        - end_date: str | dt.date 结束日期 (23:59:59)
        - columns: List[COLUMNS_LITERAL] | 'all' 列名，'all'表示所有列
        - adjustment_factor: Literal['none', 'pre', 'post'] 复权因子
          当前仅支持 'none' 与 'post'（复权因子表中实际存储的是 post_adjustment_factor）
          复权因子缺失时返回NaN（不再默认填充1.0）

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
          注意：表结构中不含code列，如需code请自行添加 df['code'] = code
    '''
    # 代码参数
    if not isinstance(code, str) or not code:
        raise ValueError('code不能为空')
    etf_list = get_etf_list()
    if code not in etf_list:
        raise ValueError(f'code: {code} 不在ETF分钟线表列表中')

    # 日期参数（使用公共工具）
    start_date = _minutely_trade_data_query.as_date(start_date, field_name='start_date')
    end_date = _minutely_trade_data_query.as_date(
        end_date,
        field_name='end_date',
        default=dt.date.today(),
    )
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')

    start_datetime = _minutely_trade_data_query.as_datetime(
        start_date, field_name='start_datetime', default_time=dt.time(0, 0, 0)
    )
    end_datetime = _minutely_trade_data_query.as_datetime(
        end_date, field_name='end_datetime', default_time=dt.time(23, 59, 59)
    )

    # 复权参数
    if adjustment_factor not in ('none', 'pre', 'post'):
        raise ValueError("adjustment_factor必须是'none'、'pre'或'post'")
    if adjustment_factor == 'pre':
        raise ValueError(
            "当前复权因子表中存储的是后复权因子(post_adjustment_factor)，"
            "请使用 adjustment_factor='post' 或 'none'"
        )

    # 列参数
    # 分钟线表结构特殊：每个code对应一张独立的表 (minutely_trade_data_{code})
    # 表中不含code列，严格按照用户columns返回（不自动添加虚拟列）
    if columns == 'all':
        selected_columns = '*'
    else:
        if not columns:
            raise ValueError('columns不能为空')
        invalid_columns = [col for col in columns if col not in ALL_COLUMNS]
        if invalid_columns:
            raise ValueError(f'columns: {invalid_columns} 非法')
        
        # 内部强制包含 trade_datetime（复权逻辑需要）
        internal_columns = list(columns)
        if 'trade_datetime' not in internal_columns:
            internal_columns = ['trade_datetime'] + internal_columns
        selected_columns = ', '.join(internal_columns)

    # 查询数据
    table_name = f'minutely_trade_data_{code}'
    query = f'''
        SELECT {selected_columns}
        FROM {table_name}
        WHERE trade_datetime BETWEEN ? AND ?
        ORDER BY trade_datetime
    '''
    params = (start_datetime, end_datetime)
    df = _minutely_trade_data_query.read_sql(query, params)

    # 无复权或空结果，直接返回
    if adjustment_factor == 'none' or df.empty:
        # 不自动添加code列（保持与数据库表结构严格一致）
        # 如果用户想要code，需要自行添加：df['code'] = code
        if isinstance(columns, list) and 'trade_datetime' not in columns and 'trade_datetime' in df.columns:
            df = df.drop(columns=['trade_datetime'])
        return df

    # 应用复权（当前使用 post_adjustment_factor）
    # 注意：_apply_adjustment 中会根据 trade_datetime 生成 trade_date 用于和因子表关联
    df = _apply_adjustment(
        df=df,
        codes=[code],
        start_date=start_date,
        end_date=end_date,
        adjustable_columns=ADJUSTABLE_COLUMNS
    )

    # 恢复 trade_datetime 格式
    if 'trade_datetime' in df.columns:
        df['trade_datetime'] = pd.to_datetime(df['trade_datetime']).dt.strftime('%Y-%m-%d %H:%M:%S')

    return df
