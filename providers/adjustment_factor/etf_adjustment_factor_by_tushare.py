'''
通过TuShare获取ETF复权因子  

更新时间：未知，收盘后收集保险  
限流：未知，用tushare通用限流器即可，单次限2000条  

API: pro.fund_adj
参数: ts_code, start_date, end_date
返回: pandas.DataFrame
    - ts_code: str
    - trade_date: str
    - adjustment_factor: float

'''
# 库
import os
import datetime as dt
import pandas as pd
import tushare as ts
from typing import Any, Literal, Tuple
from collections import Counter

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
from dotenv import load_dotenv
load_dotenv()
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')

# 兜底记录
_FALLBACK_KEY_ORIGINAL_TABLE = 'FETCH_FAILED_USE_ORIGINAL_TABLE' # 失败后，用原来的表兜底
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_CODE_888888_TODAY' # 用一个888888_today代码兜底
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_CODE_888888_TODAY' # 校验失败，用一个888888_today代码兜底

# 异常
from exceptions.api_error.tushare_error import (
    TushareETFExchangeNotFoundError,
    TushareETFAdjustmentFactorError,
    TushareETFAdjustmentDataFormatError,
    TushareQuotaExhaustedError,
    TushareTokenError,
    TushareProClientError
)

# 日志
from utils.logs import get_logger
logger = get_logger('etf_adjustment_factor_by_tushare')

# Tushare客户端
_pro: Any = None
def _get_pro() -> Any:
    '''
    懒加载 TuShare pro 客户端，避免每次 fetch 重复初始化。
    '''
    global _pro
    if _pro is None:
        if not TUSHARE_TOKEN:
            raise TushareTokenError('TuShare TOKEN未设置')
        try:
            ts.set_token(TUSHARE_TOKEN)
            _pro = ts.pro_api()
        except Exception as e:
            raise TushareProClientError(f'设置TuShare API Token失败: {e}') from e
    return _pro

# 获取ETF复权因子
@retry((TushareETFAdjustmentFactorError, TushareProClientError), retry_delay=60)
@limit('tushare')
def fetch(
    codes:str | Literal['all'] = "all",
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today()
)->pd.DataFrame:
    '''
    获取ETF复权因子  

    - 参数
        - codes: str，ETF代码，六位代码即可，会匹配后缀
        - start_date: dt.date 默认当天
        - end_date: dt.date 默认当天

    - 抛出
        - TushareETFAdjustmentFactorError: TuShare ETF复权因子错误 
        - TushareETFAdjustmentDataFormatError: TuShare ETF复权因子数据格式错误
        - TushareTokenError: TuShare APIToken错误
    '''
    try:
        pro = _get_pro()
    except TushareProClientError as e:
        logger.warning('Tushare Pro客户端初始化失败，准备重试')
        raise
    except TushareTokenError as e:
        raise
    
    try:
        if codes == 'all':
            codes = "" # 空字符串表示所有ETF
        else:
            exchange = etf_info.get_etf_info_by_code(codes)
            if not exchange.empty:
                exchange = exchange['exchange'].iloc[0]
                codes = codes + '.' + exchange.upper()
            else:
                raise TushareETFExchangeNotFoundError(f'ETF交易所未找到: {codes}')
        start_date_format = start_date.strftime('%Y%m%d')
        end_date_format = end_date.strftime('%Y%m%d')
        df = pro.fund_adj(ts_code=codes, start_date=start_date_format, end_date=end_date_format)
    except Exception as e:
        raise TushareETFAdjustmentFactorError(f'获取ETF复权因子失败: {e}')
    
    if df.empty:
        raise TushareETFAdjustmentDataFormatError(f'获取ETF复权因子为空: {codes}, {start_date}, {end_date}')
    if not all(col in df.columns for col in ['ts_code', 'trade_date', 'adj_factor']):
        raise TushareETFAdjustmentDataFormatError(f'获取ETF复权因子数据字段错误: {codes}, {start_date}, {end_date}')

    # Tushare 返回多为 object / float，与 np.str_ 整列 dtype 不一致；统一转成与 TableSchema 兼容类型
    try:
        # 重命名列
        df.rename(
            {
                'ts_code': 'code',
                'trade_date': 'trade_date',
                'adj_factor': 'adjustment_factor',
            },
            axis=1,
            inplace=True
        )
        df['code'] = df['code'].astype(str)
        df['trade_date'] = df['trade_date'].astype(str)
        df['adjustment_factor'] = pd.to_numeric(
            df['adjustment_factor'], errors='raise'
        ).astype('float64')
    except (ValueError, TypeError, KeyError) as e:
        raise TushareETFAdjustmentDataFormatError(
            f'获取ETF复权因子数据格式错误: {codes}, {start_date}, {end_date}'
        ) from e

    # 处理df 
    # 1.重命名列
    # 2.code列会有后缀和乱码，所以按顺序提取数字部分即可  
    # 3.trade_date由%Y%m%d格式转为%Y-%m-%d格式
    # 4.code-trade_date列为主键，需要去重
    # 5.和etf_info关联，仅获取etf_info表中存在的代码
    try:
        df['code'] = df['code'].str.extract(r'(\d+)')[0]
        df['trade_date'] = df['trade_date'].apply(lambda x: dt.datetime.strptime(x, '%Y%m%d').date())
        df = df.drop_duplicates(subset=['code', 'trade_date'])
        df = df[df['code'].isin(ETF_LIST)]
    except Exception as e:
        raise TushareETFAdjustmentDataFormatError(f'处理ETF复权因子数据格式错误: {codes}, {start_date}, {end_date}: {e}') from e
    return df

def _handle_error(
    codes: str | Literal['all'] = "all",
    end_date: dt.date = dt.date.today()
) -> pd.DataFrame:
    '''
    处理错误：用“当前最新交易日（本地已落库的最近一日）复权因子”兜底目标日
    '''
    target_date = end_date if isinstance(end_date, dt.date) else dt.date.today()
    if codes == 'all':
        codes = ETF_LIST
    elif isinstance(codes, str):
        codes = [codes]

    if not codes:
        raise ValueError('codes不能为空')

    latest_df = etf_adjustment_factor.get_latest_etf_adjustment_factor(
        codes=codes,
        columns=['code', 'trade_date', 'adjustment_factor']
    )
    if latest_df.empty:
        raise ValueError('本地最新复权因子为空，无法兜底')

    latest_df['trade_date'] = target_date.strftime('%Y-%m-%d')
    latest_df['adjustment_factor'] = pd.to_numeric(
        latest_df['adjustment_factor'], errors='coerce'
    ).fillna(0.0)
    latest_df = latest_df[['code', 'trade_date', 'adjustment_factor']]
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
    code_list = ETF_LIST if codes == 'all' else [codes]
    final_fallback_df = pd.DataFrame(
        {
            'code': code_list,
            'trade_date': [dt.date.today().strftime('%Y-%m-%d')] * len(code_list),
            'adjustment_factor': [0.0] * len(code_list),
        }
    )

    try:
        df = fetch(codes, start_date, end_date)
    except (
        TushareETFAdjustmentFactorError,
        TushareQuotaExhaustedError,
        TushareTokenError,
        TushareProClientError,
    ) as e:
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