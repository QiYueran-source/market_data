'''
从stock_api获取交易日历数据  

更新时间：早上9:00  
限流：40次/min  
'''
# 引入库
import json
from collections import Counter
import datetime as dt

import pandas as pd
import requests
from typing import Tuple

# 工具
from providers.provider_utils import limit, retry
from utils.schema import validate

# 表结构
from schema.trade_calendar import STOCKAPI_TRADE_CALENDAR_SCHEMA

# 数据库常量
from schema.trade_calendar import AKSHARE_TRADE_CALENDAR_SCHEMA

# api
from db.api.trade_calendar import stock_api_trade_calendar

# 日志
from utils import get_logger
logger = get_logger('trade_calendar_by_stock_api')

# 异常
from exceptions.api_error.base_error import BadRequestError, NotFoundError
from exceptions.api_error.stock_api_error import (
    StockApiQuotaExhaustedError,
    UnexpectedApiCodeError,
    DataEmptyError,
    WrongDataError,
    WrongIsOpenRangeError,
    SQLiteError,
    FallBackDataEmptyError,
)

# 获取变量的
STOCKAPI_TRADE_CALENDAR_URL = "https://www.stockapi.com.cn/v1/base/tradeDate"
_STOCKAPI_SUCCESS_CODE = 20000
_STOCKAPI_QUOTA_CODE = 88886
_REQUEST_TIMEOUT_SEC = 30

# 单次 fetch_and_clean 的兜底计数 key（仅在实际发生对应分支时写入 dict）
_FALLBACK_KEY_AKSHARE = 'FETCH_FAILED_USE_AKSHARE'  # API 失败后 Akshare 表兜底成功
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_FINAL_MINUS_ONE'  # API + 兜底查询均失败，is_open=-1
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_MINUS_ONE'  # 校验失败，is_open=-1


@retry((UnexpectedApiCodeError,DataEmptyError,WrongDataError,WrongIsOpenRangeError))
@limit('stock_api_trade_calendar')
def fetch(date: dt.date | str) -> int:
    '''用requests获取stock_api的交易日历数据'''
    if isinstance(date, str):
        date = dt.datetime.strptime(date, '%Y-%m-%d').date()
    try:
        response = requests.get(
            STOCKAPI_TRADE_CALENDAR_URL,
            params = {'tradeDate': date.strftime('%Y-%m-%d')},
            timeout=_REQUEST_TIMEOUT_SEC,
        )
    except requests.RequestException as e:
        raise BadRequestError(f'{STOCKAPI_TRADE_CALENDAR_URL} 请求失败: {e}') from e

    status_code = response.status_code
    if status_code == 404:
        raise NotFoundError(f'{STOCKAPI_TRADE_CALENDAR_URL} URL不存在，状态码: {status_code}')
    if status_code != 200:
        raise BadRequestError(f'{STOCKAPI_TRADE_CALENDAR_URL} 返回了错误的状态码: {status_code}')

    try:
        rst = response.json()
    except json.JSONDecodeError as e:
        raise WrongDataError('响应体不是合法 JSON') from e

    if not isinstance(rst, dict):
        raise WrongDataError('响应根节点不是 JSON 对象')

    # 解析响应业务码
    code = rst.get('code', 0)
    if code == _STOCKAPI_QUOTA_CODE:
        raise StockApiQuotaExhaustedError(f'请求次数超过限额: {code}')
    if code != _STOCKAPI_SUCCESS_CODE:
        raise UnexpectedApiCodeError(f'意外的 API 业务码: {code}')

    # 解析数据
    data = rst.get('data')
    if not isinstance(data, dict):
        raise WrongDataError('data 字段不是字典')
    if not data:
        raise DataEmptyError('data 字段为空')
    if 'isTradeDate' not in data:
        raise WrongDataError('data 中缺少 isTradeDate 字段')
    is_open = data['isTradeDate']
    if is_open not in (0, 1):
        raise WrongIsOpenRangeError(f'is_open 范围错误: {is_open}')

    return is_open


def _handle_error()->pd.DataFrame:
    '''
    兜底逻辑，用akshare表中的数据作为备选，处理错误
    '''
    try:
        df = stock_api_trade_calendar.get_trade_calendar_by_date(dt.date.today())
    except Exception as e:
        raise SQLiteError(f'sqlite兜底查询失败: {e}') from e
    if df.empty:
        raise FallBackDataEmptyError(f'akshare表中没有{dt.date.today()}数据')
    
    return df


def fetch_and_clean(date: dt.date | str)->Tuple[pd.DataFrame,Counter]:
    '''
    获取fetch，处理异常，整理为TableSchema格式

    返回：
    - pd.DataFrame: 交易日历数据
    - Counter: 兜底记录，key:兜底原因，value:兜底次数（仅含本次调用中发生过的项）
    '''
    records = Counter()
    try:
        is_open = fetch(date)
        df = pd.DataFrame({
            'calendar_date': [date],
            'is_open': [is_open]
        })
    except Exception as e:
        # 配额用尽、URL 不存在等不应再走本地兜底，交给上层 job 处理
        if isinstance(e, (StockApiQuotaExhaustedError, NotFoundError)):
            logger.exception('Stock API 配额用尽或资源不存在(404)，不进入兜底')
            raise
        logger.exception('API 拉取失败，进入兜底逻辑')
        try:
            df = _handle_error()
            records[_FALLBACK_KEY_AKSHARE] += 1
        except Exception:
            logger.exception(
                '兜底查询失败，启用最终逻辑：今日 is_open=-1，请及时处理',
            )
            df = pd.DataFrame({
                'calendar_date': [dt.date.today()],
                'is_open': [-1]
            })
            records[_FALLBACK_KEY_FINAL] += 1
    # 验证df
    try:
        validate(df, STOCKAPI_TRADE_CALENDAR_SCHEMA)
    except Exception:
        logger.exception('校验失败，采用兜底：今日 is_open=-1，请及时处理')
        df = pd.DataFrame({
            'calendar_date': [dt.date.today()],
            'is_open': [-1]
        })
        records[_FALLBACK_KEY_VALIDATE] += 1
    return df, records


def provide(date: dt.date | str = dt.date.today())->Tuple[pd.DataFrame, Counter, int]:
    '''
    提供给storage层的数据   
    交易日历为单条记录，用clean获取一次    
    会汇总所有调用中的兜底记录，返回provide层总兜底次数    

    返回：
    - pd.DataFrame: 交易日历数据  
    - Counter: 兜底记录，key:兜底原因，value:兜底次数  
    - int: 总获取次数
    '''
    # 总兜底计数器，用于汇总所有兜底记录  
    provide_total_fallback_records = Counter()

    # 总次数计数器
    total_fetch_times = 0

    # 获取数据与兜底记录  
    df, fallback_records = fetch_and_clean(date)
    provide_total_fallback_records.update(fallback_records)
    total_fetch_times += 1

    # 返回数据与总兜底记录  
    return df, provide_total_fallback_records, total_fetch_times
    
    

        