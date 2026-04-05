'''
从stock_api获取交易日历数据  

更新时间：早上9:00  
限流：40次/min  
'''
# 引入库
import os
import pandas as pd
import sqlite3 
import json
import datetime as dt
import requests

# 工具
from providers.provider_utils import limit, retry
from schema.schema_utils import validate

# 表结构
from schema.trade_calendar import STOCKAPI_TRADE_CALENDAR_SCHEMA

# 数据库常量
from db import DB_DIR
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
    FallBackError,
    SQLiteError,
    FallBackDataEmptyError
)

# 获取变量的
STOCKAPI_TRADE_CALENDAR_URL = "https://www.stockapi.com.cn/v1/base/tradeDate"
_STOCKAPI_SUCCESS_CODE = 20000
_STOCKAPI_QUOTA_CODE = 88886
_REQUEST_TIMEOUT_SEC = 30

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


def _handle_error():
    '''
    兜底逻辑，用akshare表中的数据作为备选，处理错误
    '''
    # 连接数据库
    db_name = AKSHARE_TRADE_CALENDAR_SCHEMA.database_name

    # 读取akshare表中的数据
    query = f'''
        SELECT calendar_date, is_open 
        FROM {AKSHARE_TRADE_CALENDAR_SCHEMA.table_name}
        WHERE calendar_date = '{dt.date.today()}'
    '''
    try:
        df = stock_api_trade_calendar.get_trade_calendar_by_date(dt.date.today())
    except Exception as e:
        raise SQLiteError(f'sqlite兜底查询失败: {e}') from e
    if df.empty:
        raise FallBackDataEmptyError(f'akshare表中没有{dt.date.today()}数据')
    
    return df


def fetch_and_clean(date: dt.date | str)->pd.DataFrame:
    '''
    获取fetch，处理异常，整理为TableSchema格式
    '''
    # 处理错误
    try:
        is_open = fetch(date)
        df = pd.DataFrame({
            'calendar_date': [date],
            'is_open': [is_open]
        })
    except Exception as e:
        logger.error(f'{e}，进入兜底逻辑')
        try:
            df = _handle_error()
        except Exception as inner_error:
            logger.error(f'{inner_error}，启用最终兜底逻辑，设置今天的is_open为-1，请及时处理') # 捕获错误，最终兜底，设置今天的is_open为-1
            df = pd.DataFrame({
                'calendar_date': [dt.date.today()],
                'is_open': [-1]
            })
            
    # 验证df
    try:
        validate(df, STOCKAPI_TRADE_CALENDAR_SCHEMA)
    except Exception as e:
        logger.error(f'{e},采用兜底，请及时处理')
        df = pd.DataFrame({
            'calendar_date': [dt.date.today()],
            'is_open': [-1]
        })
    return df


def provide(date: dt.date | str = dt.date.today())->pd.DataFrame:
    '''
    提供给storage层的数据  
    交易日历为单条记录，用clean获取一次
    '''
    df = fetch_and_clean(date)
    return df
    
    

        