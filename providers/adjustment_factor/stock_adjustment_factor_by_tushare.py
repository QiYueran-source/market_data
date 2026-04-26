'''
通过TuShare获取股票复权因子

API: pro.adj_factor
参数: ts_code, start_date, end_date
返回: pandas.DataFrame
    - ts_code: str
    - trade_date: str
    - adj_factor: float
'''

import os
import datetime as dt
from typing import List, Tuple
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import tushare as ts
from dotenv import load_dotenv

from db.api.security_info import stock_info
from providers.provider_utils import limit, retry
from models.table_schema import validate
from schema.adjustment_factor import STOCK_ADJUSTMENT_FACTOR_SCHEMA
from exceptions.api_error.tushare_error import (
    TushareQuotaExhaustedError,
    TushareTokenError,
    TushareProClientError,
    TushareStockAdjustmentExchangeNotFoundError,
    TushareStockAdjustmentFactorError,
    TushareStockAdjustmentDataFormatError,
)
from utils.logs import get_logger


load_dotenv()
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')
STOCK_LIST = stock_info.get_latest_stock_list()

logger = get_logger('stock_adjustment_factor_by_tushare')

_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_CODE_888888_TODAY'
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_CODE_888888_TODAY'


def _is_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    keywords = ('quota', 'limit', '频率', '限额', '权限', '每分钟最多访问')
    return any(k in message for k in keywords)


@retry((TushareStockAdjustmentFactorError, TushareProClientError), retry_delay=60)
@limit('tushare')
def fetch(
    code: str,
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today()
) -> pd.DataFrame:
    '''
    获取股票复权因子。

    - 参数
        - code: str，股票代码（六位无后缀）
        - start_date: 起始日期
        - end_date: 结束日期

    - 抛出
        - TushareStockAdjustmentExchangeNotFoundError: 无法匹配交易所
        - TushareStockAdjustmentFactorError: TuShare 接口调用失败
        - TushareQuotaExhaustedError: TuShare 额度/频控问题
        - TushareStockAdjustmentDataFormatError: 返回数据为空/缺列/类型异常
        - TushareTokenError, TushareProClientError: 客户端初始化问题
    '''
    if not TUSHARE_TOKEN:
        raise TushareTokenError('TuShare TOKEN未设置')
    try:
        ts.set_token(TUSHARE_TOKEN)
    except Exception as e:
        raise TushareProClientError(f'设置TuShare API Token失败: {e}') from e

    raw_code = str(code).strip()
    try:
        info_df = stock_info.get_stock_info_by_code(raw_code)
        if info_df.empty:
            raise TushareStockAdjustmentExchangeNotFoundError(
                f'股票交易所未找到: {raw_code}'
            )
        exchange = str(info_df['exchange'].iloc[0]).upper()
        ts_code = f'{raw_code}.{exchange}'

        start_date_fmt = start_date.strftime('%Y%m%d')
        end_date_fmt = end_date.strftime('%Y%m%d')
        df = ts.pro_bar(
            ts_code=ts_code,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            asset='E',
            adj='qfq',
            freq='D',
            adjfactor=True,
        )
    except TushareStockAdjustmentExchangeNotFoundError:
        raise
    except Exception as e:
        if _is_quota_error(e):
            raise TushareQuotaExhaustedError(f'股票复权因子请求超限: {e}') from e
        raise TushareStockAdjustmentFactorError(f'获取股票复权因子失败: {e}') from e

    if df is None or df.empty:
        raise TushareStockAdjustmentDataFormatError(
            f'获取股票复权因子为空: {raw_code}, {start_date}, {end_date}'
        )
    if not all(col in df.columns for col in ('ts_code', 'trade_date', 'adj_factor')):
        raise TushareStockAdjustmentDataFormatError(
            f'股票复权因子返回字段错误: {raw_code}, {start_date}, {end_date}'
        )

    try:
        df = df.rename(
            columns={
                'ts_code': 'code',
                'trade_date': 'trade_date',
                'adj_factor': 'adjustment_factor',
            }
        )
        df['code'] = df['code'].astype(str).str.extract(r'(\d+)')[0]
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d').dt.strftime('%Y-%m-%d')
        df['adjustment_factor'] = pd.to_numeric(
            df['adjustment_factor'], errors='coerce'
        ).fillna(0.0).astype('float64')
        df = df.drop_duplicates(subset=['code', 'trade_date'])
        df = df[df['code'].isin(STOCK_LIST)]
        df = df[['code', 'trade_date', 'adjustment_factor']]
    except Exception as e:
        raise TushareStockAdjustmentDataFormatError(
            f'处理股票复权因子数据格式错误: {raw_code}, {start_date}, {end_date}: {e}'
        ) from e

    if df.empty:
        raise TushareStockAdjustmentDataFormatError(
            f'股票复权因子清洗后为空: {raw_code}, {start_date}, {end_date}'
        )
    return df.reset_index(drop=True)


def fetch_and_clean(
    code: str,
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today()
) -> Tuple[pd.DataFrame, Counter]:
    '''
    获取股票复权因子并清洗。

    当前阶段不启用原表回填兜底；fetch 或 validate 失败时直接使用最终兜底数据。
    '''
    records = Counter()
    final_fallback_df = pd.DataFrame(
        {
            'code': [str(code)],
            'trade_date': [end_date.strftime('%Y-%m-%d')],
            'adjustment_factor': [0.0],
        }
    )

    try:
        df = fetch(code=code, start_date=start_date, end_date=end_date)
    except (
        TushareStockAdjustmentFactorError,
        TushareStockAdjustmentDataFormatError,
        TushareStockAdjustmentExchangeNotFoundError,
        TushareQuotaExhaustedError,
        TushareTokenError,
        TushareProClientError,
    ) as e:
        logger.exception(f'获取股票复权因子并清洗失败(code={code}): {e}')
        df = final_fallback_df
        records[_FALLBACK_KEY_FINAL] += 1

    try:
        validate(df, STOCK_ADJUSTMENT_FACTOR_SCHEMA)
    except Exception as e:
        logger.exception(f'校验股票复权因子失败(code={code}): {e}')
        df = final_fallback_df
        records[_FALLBACK_KEY_VALIDATE] += 1

    return df, records


def provide(
    codes: List[str] | None = None,
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today(),
    max_workers: int = 10,
) -> Tuple[pd.DataFrame, Counter, int]:
    '''
    提供股票复权因子数据。
    '''
    total_fetch_times = 0
    total_fallback_records = Counter()
    code_list = codes if codes is not None else STOCK_LIST
    normalized_codes = []
    seen = set()
    for code in code_list:
        c = str(code).strip()
        if not c or c in seen:
            continue
        seen.add(c)
        normalized_codes.append(c)

    if not normalized_codes:
        empty_df = pd.DataFrame(columns=['code', 'trade_date', 'adjustment_factor'])
        return empty_df, total_fallback_records, total_fetch_times

    tasks = [(code, start_date, end_date) for code in normalized_codes]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_and_clean, *task) for task in tasks]
        results = [future.result() for future in futures]

    frames = []
    for df, fallback_records in results:
        if df is None or df.empty:
            continue
        frames.append(df)
        total_fallback_records.update(fallback_records)
        total_fetch_times += 1

    if frames:
        merged_df = pd.concat(frames, ignore_index=True)
    else:
        merged_df = pd.DataFrame(columns=['code', 'trade_date', 'adjustment_factor'])

    return merged_df, total_fallback_records, total_fetch_times