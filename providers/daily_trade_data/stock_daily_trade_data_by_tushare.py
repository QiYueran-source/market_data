'''
通过 TuShare 获取股票日线数据（`ts.pro_bar`）。

更新时间：收盘后增量更新
限流：tushare（见 provider_utils.api_limiter）
'''
# 库
import datetime as dt
import os
import re
from bisect import bisect_left
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Any, List, Tuple
import numpy as np
import pandas as pd
import tushare as ts

# 环境变量
from dotenv import load_dotenv
load_dotenv()
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN')

# 工具
from providers.provider_utils import limit, retry
from models.table_schema import validate
from schema.daily_trade_data import STOCK_DAILY_TRADE_DATA_SCHEMA
from db.api.security_info import stock_info
from db.api.trade_calendar import stock_api_trade_calendar

# 规定字段
REQUIRED_FIELDS_SET = {'ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount'}

# 兜底记录
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_FALLBACK_ZERO'
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_FALLBACK_ZERO'

# 最新股票列表（快照）
LATEST_STOCK_LIST = set(stock_info.get_latest_stock_list())

# 常量
TRADE_DATE_LIST = stock_api_trade_calendar.get_trade_date_list(end_date = dt.date.today())
TRADE_DATE_LIST_SORTED = sorted(set(TRADE_DATE_LIST))
REAL_FLOAT_DECIMALS = 6
SCHEMA_COLS = STOCK_DAILY_TRADE_DATA_SCHEMA.cols

# 日志
from utils.logs import get_logger
logger = get_logger('stock_daily_trade_data_by_tushare')

# 异常
from exceptions.api_error.tushare_error import (
    TushareProClientError,
    TushareQuotaExhaustedError,
    TushareStockDailyEmptyError,
    TushareStockDailyFormatError,
    TushareStockDailyProBarError,
    TushareStockNotInListError,
    TushareStockExchangeNotFoundError,
    TushareTokenError,
)

def _is_quota_error(exc: Exception) -> bool:
    message = str(exc).lower()
    keywords = ('quota', 'limit', '频率', '限额', '权限', '每分钟最多访问')
    return any(k in message for k in keywords)

def normalize_trade_date(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().replace('-', '')
    if len(s) != 8 or not s.isdigit():
        return None
    return f'{s[:4]}-{s[4:6]}-{s[6:8]}'

def get_fetch_start_date(start_date: dt.date) -> dt.date:
    if not TRADE_DATE_LIST_SORTED:
        return start_date
    idx = bisect_left(TRADE_DATE_LIST_SORTED, start_date)
    if idx <= 0:
        return start_date
    return TRADE_DATE_LIST_SORTED[idx - 1]

def clean_daily_frame(df: pd.DataFrame, code: str, open_dates: set[str]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out['code'] = code
    out['trade_date'] = out['trade_date'].map(normalize_trade_date)
    out = out.dropna(subset=['trade_date'])

    if open_dates:
        out = out[out['trade_date'].isin(open_dates)]

    # 你是单 code 拉取，这里按 trade_date 去重即可
    out = out.sort_values('trade_date').drop_duplicates(subset=['trade_date'], keep='last')
    return out

def _round_real_series(x: pd.Series | np.ndarray) -> pd.Series:
    ser = pd.Series(x, dtype='float64') if isinstance(x, np.ndarray) else x
    return pd.to_numeric(ser, errors='coerce').round(REAL_FLOAT_DECIMALS).astype('float64')

def to_stock_schema_dataframe(cleaned: pd.DataFrame) -> pd.DataFrame:
    if cleaned.empty:
        return pd.DataFrame(columns=SCHEMA_COLS)

    d = cleaned.sort_values('trade_date').reset_index(drop=True).copy()
    o = pd.to_numeric(d['open'], errors='coerce')
    h = pd.to_numeric(d['high'], errors='coerce')
    low = pd.to_numeric(d['low'], errors='coerce')
    c = pd.to_numeric(d['close'], errors='coerce')
    ycp = c.shift(1)
    up = c - ycp
    mask = ycp.notna() & (ycp != 0)
    udr = np.where(mask, up / ycp, np.nan)
    amp = np.where(mask, (h - low) / ycp, np.nan)

    vol_hand = pd.to_numeric(d['vol'], errors='coerce')
    volume = (vol_hand * 100).round().astype('Int64')
    amt_k = pd.to_numeric(d['amount'], errors='coerce')
    amount_yuan = amt_k * 1000.0

    n = len(d)
    out = pd.DataFrame(
        {
            'code': d['code'].astype(str),
            'trade_date': d['trade_date'].astype(str),
            'open': _round_real_series(o),
            'high': _round_real_series(h),
            'low': _round_real_series(low),
            'close': _round_real_series(c),
            'volume': volume,
            'amount': _round_real_series(amount_yuan),
            'original_volume': pd.Series([0] * n, dtype='Int64'),
            'yesterday_close_price': _round_real_series(ycp),
            'up_down': _round_real_series(up),
            'up_down_rate': _round_real_series(udr),
            'amplitude': _round_real_series(amp),
            'turnover_rate': _round_real_series(np.full(n, 0.0)),
            'pe_ratio': _round_real_series(np.full(n, 0.0)),
        }
    )
    return out[SCHEMA_COLS]

@retry((TushareStockDailyProBarError), max_attempts=3, retry_delay=60.0)
@limit('tushare')
def fetch(
    code: str,
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today(),
) -> pd.DataFrame:
    '''
    获取股票日线原始数据（TuShare pro_bar）。
    '''
    # 检查是否有code
    if code not in LATEST_STOCK_LIST:
        raise TushareStockNotInListError(f'代码{code}不在最新股票列表中')
    
    # 交易所
    exchange = stock_info.get_stock_info_by_code(code)
    if exchange.empty:
        raise TushareStockExchangeNotFoundError(f'交易所未找到: {code}')
    else:
        exchange = exchange['exchange'].iloc[0]
        code = code + '.' + exchange.upper()
    
    # API验证
    if not TUSHARE_TOKEN:
        raise TushareTokenError('TuShare TOKEN未设置')
    try:
        ts.set_token(TUSHARE_TOKEN)
    except Exception as e:
        raise TushareProClientError(f'设置TuShare API Token失败: {e}') from e

    try:
        df = ts.pro_bar(
            ts_code=code,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d'),
            asset='E',
            adj=None,
            freq='D',
            adjfactor=False,
        )
    # pro_bar没有管理超额的异常，自定义一个
    except Exception as e:
        if _is_quota_error(e):
            raise TushareQuotaExhaustedError(f'TuShare pro_bar 请求超限: {code}: {e}') from e
        raise TushareStockDailyProBarError(f'TuShare pro_bar 失败: {code}: {e}') from e

    if df is None or df.empty:
        raise TushareStockDailyEmptyError(f'股票日线返回为空: {code}')

    missing_required = sorted(REQUIRED_FIELDS_SET - set(df.columns))
    if missing_required:
        raise TushareStockDailyFormatError(
            f'股票日线缺少必填字段: {missing_required}，实际字段: {sorted(df.columns)}'
        )

    return df


def fetch_and_clean(
    code: str,
    start_date: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today(),
    open_dates: set[str] | None = None,
) -> Tuple[pd.DataFrame, Counter]:
    '''
    获取股票日线并清洗。
    '''
    records = Counter()
    final_fallback_df = pd.DataFrame(
        {
            'code': [str(code)],
            'trade_date': [end_date.strftime('%Y-%m-%d')],
            'open': [0.0],
            'high': [0.0],
            'low': [0.0],
            'close': [0.0],
            'volume': [0],
            'amount': [0.0],
            'original_volume': [0],
            'yesterday_close_price': [0.0],
            'up_down': [0.0],
            'up_down_rate': [0.0],
            'amplitude': [0.0],
            'turnover_rate': [0.0],
            'pe_ratio': [0.0],
        }
    )

    if start_date > end_date:
        return pd.DataFrame(), records

    fetch_start = get_fetch_start_date(start_date)

    try:
        raw = fetch(code, fetch_start, end_date)
        cleaned = clean_daily_frame(raw, code, open_dates or set())
        df = to_stock_schema_dataframe(cleaned)
        start_s = start_date.strftime('%Y-%m-%d')
        end_s = end_date.strftime('%Y-%m-%d')
        df = df[(df['trade_date'] >= start_s) & (df['trade_date'] <= end_s)]
        if df.empty:
            raise TushareStockDailyEmptyError(f'清洗后为空: {code}')
    except TushareStockNotInListError:
        logger.warning('股票代码%s不在最新列表，跳过', code)
        return pd.DataFrame(), records
    except Exception:
        logger.exception('拉取或清洗失败，stock_code=%s，进入兜底逻辑', code)
        df = final_fallback_df
        records[_FALLBACK_KEY_FINAL] += 1

    try:
        validate(df, STOCK_DAILY_TRADE_DATA_SCHEMA)
    except Exception:
        logger.exception('校验失败，采用兜底：stock_code=%s，请及时处理', code)
        df = final_fallback_df
        records[_FALLBACK_KEY_VALIDATE] += 1

    return df, records


def provide(
    codes: List[str],
    bootstrap_start: dt.date = dt.date.today(),
    end_date: dt.date = dt.date.today(),
    max_workers: int = 10,
) -> Tuple[pd.DataFrame, Counter, int]:
    '''
    提供股票日线数据。

    - codes: 股票代码列表
    - return:
        - df: 日线数据 DataFrame
        - total_fallback_records: 兜底记录
        - total_fetch_times: 总获取次数
    '''
    comb_df = None
    total_fetch_times = 0
    total_fallback_records = Counter()

    if not codes:
        return pd.DataFrame(), total_fallback_records, total_fetch_times

    fetch_start = get_fetch_start_date(bootstrap_start)
    open_dates = {
        d.strftime('%Y-%m-%d')
        for d in TRADE_DATE_LIST
        if fetch_start <= d <= end_date
    }
    if not open_dates:
        logger.warning(f'交易日历为空，区间 {fetch_start} ~ {end_date}，可能触发大量兜底')

    tasks = []
    for code in codes:
        c = str(code).strip()
        tasks.append((c, bootstrap_start, end_date, open_dates))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_and_clean, *task) for task in tasks]
        results = [future.result() for future in futures]

    for df, records in results:
        if df is None or df.empty:
            continue
        if comb_df is None:
            comb_df = df
        else:
            comb_df = pd.concat([comb_df, df], ignore_index=True)
        total_fallback_records.update(records)
        total_fetch_times += 1

    if comb_df is None:
        comb_df = pd.DataFrame(columns=SCHEMA_COLS)
    return comb_df, total_fallback_records, total_fetch_times
