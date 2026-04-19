'''
ETF日线交易数据API  
- get_etf_daily_trade_data(): 获取ETF日线交易数据
'''
# 库
import datetime as dt
import pandas as pd
import numpy as np
from typing import List, Literal

# 常量
from db.api.adjustment_factor import etf_adjustment_factor
from db.api.security_info import etf_info
from . import _daily_trade_data_query

DB_NAME = _daily_trade_data_query.DAILY_TRADE_DATA_DB_NAME
TABLE_NAME = 'etf_daily_trade_data'

# 列
COLUMNS_LITERAL = Literal['trade_date', 'code', 'yesterday_close_price', 'open', 'high', 'low', 'close', 'volume', 'amount', 'up_down', 'up_down_rate', 'turnover_rate', 'amplitude', 'original_volume', 'pe_ratio']
ALL_COLUMNS = (
    'trade_date', 'code', 'yesterday_close_price', 'open', 'high', 'low', 'close',
    'volume', 'amount', 'up_down', 'up_down_rate', 'turnover_rate', 'amplitude',
    'original_volume', 'pe_ratio'
)
ADJUSTABLE_COLUMNS = (
    'yesterday_close_price', 'open', 'high', 'low', 'close', 'up_down'
)

def get_etf_daily_trade_data(
    codes:str |List[str],
    start_date: str | dt.date | dt.datetime | pd.Timestamp = dt.date(2020, 1, 1),
    end_date: str | dt.date | dt.datetime | pd.Timestamp | None = None,
    columns:List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor:Literal['none', 'pre', 'post'] = 'none'
)->pd.DataFrame:
    '''
    获取ETF日线交易数据

    - 参数
        - codes: str | List[str] ETF代码(列表)
        - start_date: str | dt.date 开始日期
        - end_date: str | dt.date 结束日期
        - columns: List[COLUMNS_LITERAL] | 'all' 列名，'all'表示所有列
        - adjustment_factor: Literal['none', 'pre', 'post'] 复权因子，当前仅支持 'none' 与 'post'
          复权因子缺失时返回NaN（不再默认填充1.0）

    - 返回
        - pandas.DataFrame: ETF日线交易数据
            - trade_date: str 交易日期
            - code: str ETF代码
            - yesterday_close_price: float 昨收价
            - open: float 开盘价
            - high: float 最高价
            - low: float 最低价
            - close: float 收盘价
            - volume: int 成交量
            - amount: float 成交金额
            - up_down: float 相对昨收盘涨跌额
            - up_down_rate: float 相对昨收盘涨跌率
            - turnover_rate: float 换手率
            - amplitude: float 振幅
            - original_volume: int 原始成交量
            - pe_ratio: float 市盈率
    '''
    # 代码参数
    codes = _daily_trade_data_query.normalize_codes(codes)
    etf_code_set = set(etf_info.get_etf_list())
    if not all(code in etf_code_set for code in codes):
        missing_codes = [code for code in codes if code not in etf_code_set]
        raise ValueError(f'codes: {missing_codes} 不在ETF列表中')

    # 日期参数
    start_date = _daily_trade_data_query.as_date(start_date, field_name='start_date')
    end_date = _daily_trade_data_query.as_date(
        end_date,
        field_name='end_date',
        default=dt.date.today(),
    )
    if start_date > end_date:
        raise ValueError('start_date不能大于end_date')

    # 复权参数
    if adjustment_factor not in ('none', 'pre', 'post'):
        raise ValueError("adjustment_factor必须是'none'、'pre'或'post'")
    if adjustment_factor == 'pre':
        raise ValueError("当前不支持前复权，请使用 adjustment_factor='post' 或 'none'")

    # 列参数
    selected_columns = _daily_trade_data_query.select_columns(columns, ALL_COLUMNS)

    placeholders = ','.join(['?' for _ in codes])
    query = f'''
        SELECT {selected_columns}
        FROM {TABLE_NAME}
        WHERE code IN ({placeholders})
        AND trade_date BETWEEN ? AND ?
        ORDER BY code, trade_date
    '''
    params = tuple(codes) + (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    df = _daily_trade_data_query.read_sql(query, params)

    # 无复权或空结果，直接返回
    if adjustment_factor == 'none' or df.empty:
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

    # 统一日期格式后按 code + trade_date 关联复权因子
    df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y-%m-%d')
    factor_df['trade_date'] = pd.to_datetime(factor_df['trade_date']).dt.strftime('%Y-%m-%d')
    merged = df.merge(
        factor_df,
        on=['code', 'trade_date'],
        how='left'
    )
    merged[factor_column] = pd.to_numeric(
        merged[factor_column], errors='coerce'
    )
    # 复权因子缺失时，对应的可调整价格字段也设为NaN

    # 先对所有可调整列做数值转换
    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')

    # 对有复权因子的行进行调整
    mask_has_factor = merged[factor_column].notna()
    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged.loc[mask_has_factor, col] = (
                merged.loc[mask_has_factor, col] * merged.loc[mask_has_factor, factor_column]
            )

    # 对缺失复权因子的行，将可调整的价格字段设为NaN
    mask_no_factor = merged[factor_column].isna()
    for col in ADJUSTABLE_COLUMNS:
        if col in merged.columns:
            merged.loc[mask_no_factor, col] = np.nan

    merged.drop(columns=[factor_column], inplace=True)
    df = merged
    return df

def agg_daily_price_to_weekly(
    codes: str | List[str],
    start_date: str | dt.date = dt.date(2020, 1, 1),
    end_date: str | dt.date | None = None,
    columns: List[COLUMNS_LITERAL] | Literal['all'] = 'all',
    adjustment_factor: Literal['none', 'pre', 'post'] = 'post'
) -> pd.DataFrame:
    '''
    将ETF日线数据聚合为周度数据（每周最后一个交易日）
    
    - 参数
        - codes: str | List[str] ETF代码
        - start_date, end_date: 日期范围
        - columns: 需要保留的列
        - adjustment_factor: 是否使用复权数据（推荐使用 'post'）
    
    - 返回
        - pandas.DataFrame: 周度数据，索引为每周最后一个交易日
            - trade_date: 周结束日期（每周最后一个交易日）
            - code
            - open, high, low, close (周OHLC)
            - volume, amount (周总成交量/金额)
            - 其他列：最后值
    '''
    # 1. 获取日线数据（使用复权）
    df = get_etf_daily_trade_data(
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        columns=columns,
        adjustment_factor=adjustment_factor
    )
    
    if df.empty:
        return df
    
    # 确保日期是datetime类型
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values(['code', 'trade_date'])
    
    # 2. 添加周标识（每周的最后一个交易日作为周标识）
    df['week'] = df['trade_date'].dt.to_period('W').apply(lambda x: x.end_time)
    df['week'] = pd.to_datetime(df['week'].dt.date)  # 转为date
    
    # 3. 分组聚合
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'amount': 'sum',
    }
    
    # 对其他字段使用最后一天的值
    other_cols = [col for col in df.columns if col not in ['trade_date', 'code', 'week', 'open', 'high', 'low', 'close', 'volume', 'amount']]
    for col in other_cols:
        agg_dict[col] = 'last'
    
    weekly = df.groupby(['code', 'week']).agg(agg_dict).reset_index()
    
    # 重命名 week 为 trade_date（周结束日）
    weekly = weekly.rename(columns={'week': 'trade_date'})
    weekly = weekly.sort_values(['code', 'trade_date']).reset_index(drop=True)
    
    # 调整列顺序（尽量保持与日线一致）
    if columns != 'all':
        desired_cols = ['trade_date', 'code'] + [col for col in columns if col in weekly.columns]
        weekly = weekly[desired_cols]
    
    return weekly