'''
通过TuShare获取ETF复权因子  

更新时间：未知，收盘后收集保险  
限流：未知，用tushare通用限流器即可，单次限2000条  

API: pro.fund_adj
参数: ts_code, start_date, end_date
返回: pandas.DataFrame
    - ts_code: str
    - trade_date: str
    - pre_adjustment_factor: float

'''
import os
import datetime as dt
import pandas as pd
import tushare as ts
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Any, Literal
from collections import Counter
from dotenv import load_dotenv
load_dotenv()

# 工具
from providers.provider_utils import limit, retry
from models.table_schema import validate
from db.api.security_info import etf_info
from db.api.adjustment_factor import etf_adjustment_factor

# ETF列表
ETF_LIST = etf_info.get_latest_etf_list()

# 表结构
from schema.adjustment_factor import (
    ETF_ADJUSTMENT_FACTOR_SCHEMA
)

# 环境变量
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')

# 兜底记录
_FALLBACK_KEY_ORIGINAL_TABLE = 'FETCH_FAILED_USE_ORIGINAL_TABLE' # 失败后，用原来的表兜底
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_CODE_888888_TODAY' # 用一个888888_today代码兜底
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_CODE_888888_TODAY' # 校验失败，用一个888888_today代码兜底

# 异常
from exceptions.api_error.tushare_error import (
    TushareETFAdjustmentFactorError,
    TushareETFAdjustmentDataFormatError,
    TushareQuotaExhaustedError,
    TushareTokenError
)

# 日志
import logging
logger = logging.getLogger('adjustment_factor.etf_adjustment_factor_by_tushare')

# 获取ETF复权因子
@retry((TushareQuotaExhaustedError, TushareTokenError, TushareETFAdjustmentFactorError))
@limit('tushare')
def fetch(
    codes:str | Literal['all'] = "all",
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today()
)->pd.DataFrame:
    '''
    获取ETF复权因子  

    - 参数
        - codes: str，ETF代码，需要加交易所后缀，如 513100.SH；空字符串表示所有ETF  
        - start_date: dt.date 默认当天
        - end_date: dt.date 默认当天

    - 抛出
        - TushareETFAdjustmentFactorError: TuShare ETF复权因子错误 
        - TushareETFAdjustmentDataFormatError: TuShare ETF复权因子数据格式错误
        - TushareTokenError: TuShare APIToken错误
    '''
    # 尝试设置Token  
    try:
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
    except Exception as e:
        logger.exception(f'设置TuShare API Token失败: {e}')
        raise TushareTokenError(f'设置TuShare API Token失败: {e}')

    try:
        if codes == 'all':
            codes = "" # 空字符串表示所有ETF
        start_date_format = start_date.strftime('%Y%m%d')
        end_date_format = end_date.strftime('%Y%m%d')
        df = pro.fund_adj(ts_code=codes, start_date=start_date_format, end_date=end_date_format)
    except Exception as e:
        logger.exception(f'获取ETF复权因子失败: {e}')
        raise TushareETFAdjustmentFactorError(f'获取ETF复权因子失败: {e}')
    
    if df.empty:
        logger.exception(f'获取ETF复权因子为空: {codes}, {start_date}, {end_date}')
        raise TushareETFAdjustmentDataFormatError(f'获取ETF复权因子为空: {codes}, {start_date}, {end_date}')
    if not all(col in df.columns for col in ['ts_code', 'trade_date', 'adj_factor']):
        logger.exception(f'获取ETF复权因子数据格式错误: {codes}, {start_date}, {end_date}')
        raise TushareETFAdjustmentDataFormatError(f'获取ETF复权因子数据字段错误: {codes}, {start_date}, {end_date}')

    # 重命名列
    df.rename(
        {
            'ts_code': 'code',
            'trade_date': 'trade_date',
            'adj_factor': 'pre_adjustment_factor',
        },
        axis=1,
        inplace=True
    )

    # Tushare 返回多为 object / float，与 np.str_ 整列 dtype 不一致；统一转成与 TableSchema 兼容类型
    try:
        df['code'] = df['code'].astype(str)
        df['trade_date'] = df['trade_date'].astype(str)
        df['pre_adjustment_factor'] = pd.to_numeric(
            df['pre_adjustment_factor'], errors='raise'
        ).astype('float64')
    except (ValueError, TypeError) as e:
        logger.exception(
            f'获取ETF复权因子列类型转换失败: {codes}, {start_date}, {end_date}: {e}'
        )
        raise TushareETFAdjustmentDataFormatError(
            f'获取ETF复权因子数据类型错误: {codes}, {start_date}, {end_date}'
        ) from e

    # 处理df 
    # 1.code列会有后缀和乱码，所以按顺序提取数字部分即可  
    # 2.trade_date由%Y%m%d格式转为%Y-%m-%d格式
    # 3.code-trade_date列为主键，需要去重
    # 4.和etf_info关联，仅获取etf_info表中存在的代码
    df['code'] = df['code'].str.extract(r'(\d+)')[0]
    df['trade_date'] = df['trade_date'].apply(lambda x: dt.datetime.strptime(x, '%Y%m%d').date())
    df = df.drop_duplicates(subset=['code', 'trade_date'])
    df = df[df['code'].isin(ETF_LIST)]
    return df

def _handle_error(
    codes: str | Literal['all'] = "all",
    end_date: dt.date = dt.date.today()
) -> pd.DataFrame:
    '''
    处理错误：用“前一交易日（本地已落库的最近一日）复权因子”兜底目标日
    '''
    target_date = end_date if isinstance(end_date, dt.date) else dt.date.today()
    if codes == 'all':
        codes = ETF_LIST
    elif isinstance(codes, str):
        codes = [codes]

    if not codes:
        raise ValueError('codes不能为空')

    # 统一为无后缀6位代码，便于调用 db.api 接口
    normalized_codes = []
    for code in codes:
        code_str = str(code)
        extracted = pd.Series([code_str]).str.extract(r'(\d{6})')[0].iloc[0]
        if isinstance(extracted, str):
            normalized_codes.append(extracted)
    codes = [code for code in normalized_codes if code in ETF_LIST]
    if not codes:
        raise ValueError('codes无可用ETF代码，无法兜底')

    history_end_date = target_date - dt.timedelta(days=1)
    if history_end_date < dt.date(2020, 1, 1):
        raise ValueError('没有可用历史日期用于兜底')

    history_df = etf_adjustment_factor.get_etf_adjustment_factor(
        codes=codes,
        start_date='2020-01-01',
        end_date=history_end_date,
        columns=['code', 'trade_date', 'pre_adjustment_factor']
    )

    if history_df.empty:
        raise ValueError('本地历史复权因子为空，无法兜底')

    history_df['trade_date'] = pd.to_datetime(history_df['trade_date'], errors='coerce')
    history_df = history_df.dropna(subset=['trade_date'])
    history_df = history_df.sort_values(['code', 'trade_date'])
    latest_df = history_df.groupby('code', as_index=False).tail(1)
    if latest_df.empty:
        raise ValueError('本地历史复权因子无有效日期，无法兜底')

    latest_df['trade_date'] = target_date.strftime('%Y-%m-%d')
    latest_df['pre_adjustment_factor'] = pd.to_numeric(
        latest_df['pre_adjustment_factor'], errors='coerce'
    ).fillna(0.0)
    latest_df = latest_df[['code', 'trade_date', 'pre_adjustment_factor']]
    return latest_df.reset_index(drop=True)

def fetch_and_clean(
    codes:str | Literal['all'] = "all",
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today()
)->Tuple[pd.DataFrame, Counter]:
    '''
    获取ETF复权因子并清洗
    '''
    records = Counter()
    final_fallback_df = pd.DataFrame(
        {
            'code': ['888888'],
            'trade_date': [dt.date.today().strftime('%Y-%m-%d')],
            'pre_adjustment_factor': [0.0],
        }
    )

    try:
        df = fetch(codes, start_date, end_date)
    except (TushareETFAdjustmentFactorError, TushareETFAdjustmentDataFormatError) as e:
        logger.exception(f'获取ETF复权因子并清洗失败: {e}')
        try:
            df = _handle_error(codes=codes, end_date=end_date)
            records[_FALLBACK_KEY_ORIGINAL_TABLE] += 1
        except Exception as e:
            logger.exception(f'获取ETF复权因子并清洗失败: {e}')
            df = final_fallback_df
            records[_FALLBACK_KEY_FINAL] += 1
   
    # 校验df
    try:
        validate(df, ETF_ADJUSTMENT_FACTOR_SCHEMA)
    except Exception as e:
        logger.exception(f'校验ETF复权因子失败: {e}')
        df = final_fallback_df
        records[_FALLBACK_KEY_VALIDATE] += 1

    return df, records

def provide(
    codes:str | Literal['all'] = "all",
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today()
)->Tuple[pd.DataFrame, Counter, int]:
    '''
    提供ETF复权因子
    '''
    # 总次数计数器
    total_fetch_times = 0
    total_fallback_records = Counter()

    # 获取数据与兜底记录
    df, fallback_records = fetch_and_clean(codes, start_date, end_date)
    total_fallback_records.update(fallback_records)
    total_fetch_times += 1

    # 返回数据与总兜底记录
    return df, total_fallback_records, total_fetch_times