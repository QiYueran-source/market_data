'''
从 麦蕊智数 获取股票列表信息    

更新时间：每天下午16：20  
限流：300次/min    

url: https://api.mairuiapi.com/hslt/list/您的licence

返回示例：
[{'dm': '600000', 'mc': '浦发银行', 'jys': 'SH'}, ... ]
'''
# 库
import os 
import json
import datetime as dt
import pandas as pd  
import requests
from typing import List, Dict, Tuple
from collections import Counter
from dotenv import load_dotenv
load_dotenv()

# 工具
from providers.provider_utils import limit, retry
from models.table_schema import validate
from schema.security_info import STOCK_INFO_SCHEMA
from db.api.security_info import stock_info

# 环境变量
MAIRUI_TOKEN = os.getenv('MAIRUI_TOKEN')
MAIRUI_STOCK_INFO_URL = 'https://api.mairuiapi.com/hslt/list'

# 规定字段
REQUIRED_FIELDS_SET = {'dm', 'mc', 'jys'}

# 兜底记录
_FALLBACK_KEY_ORIGINAL_TABLE = 'ORIGINAL_TABLE_FAIL' # 原始表兜底
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_CODE_888888_TODAY' # 用一个888888_today代码兜底
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_CODE_888888_TODAY' # 校验失败，用一个888888_today代码兜底

# 日志
import logging
logger = logging.getLogger('security_info.stock_info_by_mairui')

# 异常
from exceptions.api_error.base_error import NotFoundError, BadRequestError
from exceptions.api_error.mairui_error import (
    MairuiTokenEmptyError,
    MairuiQuotaExhaustedError,
    InsufficientTierError,
    InvalidLicenceError,
    StockInfoJsonDecodeError,
    StockInfoFormatError,
    StockInfoEmptyError,
    StockInfoFieldError,
)

# 获取股票列表信息
@retry((BadRequestError))
@limit('mairui')
def fetch()->List[Dict[str, str]]:
    '''
    获取股票列表信息  
    
    - 抛出
        - MairuiTokenEmptyError: 麦蕊智数TOKEN未设置
        - BadRequestError: 请求麦蕊智数API失败
        - NotFoundError: {MAIRUI_STOCK_INFO_URL} URL不存在
        - MairuiQuotaExhaustedError: {MAIRUI_STOCK_INFO_URL} 请求次数超过限额
        - InsufficientTierError: {MAIRUI_STOCK_INFO_URL} Token等级不足
        - InvalidLicenceError: {MAIRUI_STOCK_INFO_URL} licence无效
        - StockInfoFieldError: 股票列表返回值的List，内部dict的字段应该至少包含:{REQUIRED_FIELDS_SET}
        - StockInfoJsonDecodeError: 股票列表返回不是合法json
        - StockInfoFormatError: 股票列表返回格式错误，需要List[dict], 实际是{type(rst)}
        - StockInfoEmptyError: 股票列表返回值的List为空
        - StockInfoFormatError: 股票列表返回值的List，内部需要是dict，实际是{type(invalid_items[0])}
        - StockInfoFieldError: 股票列表返回值的List，内部dict的字段应该至少包含:{REQUIRED_FIELDS_SET}，实际是{invalid_keys[0].keys()}
    '''
    if not MAIRUI_TOKEN:
        raise MairuiTokenEmptyError('麦蕊智数TOKEN未设置')

    url = f'{MAIRUI_STOCK_INFO_URL}/{MAIRUI_TOKEN}'
    try:
        response = requests.get(url)
        status_code = response.status_code
        if status_code == 404:
            raise NotFoundError(f'{MAIRUI_STOCK_INFO_URL} URL不存在，状态码: {status_code}')
        if status_code == 503:
            raise MairuiQuotaExhaustedError(f'{MAIRUI_STOCK_INFO_URL} 请求次数超过限额，状态码: {status_code}')
        if status_code == 101:
            raise InsufficientTierError(f'{MAIRUI_STOCK_INFO_URL} Token等级不足，状态码: {status_code}')
        if status_code == 102:
            raise InvalidLicenceError(f'{MAIRUI_STOCK_INFO_URL} licence无效，状态码: {status_code}')
        if status_code != 200:
            raise BadRequestError(f'{MAIRUI_STOCK_INFO_URL} 返回了错误的状态码: {status_code}')
    except requests.exceptions.RequestException as e:
        raise BadRequestError(f'请求麦蕊智数API失败: {e}')
    
    try:
        rst = response.json()
    except json.JSONDecodeError as e:
        raise StockInfoJsonDecodeError(f'股票列表返回不是合法json: {e}')
    if not isinstance(rst, list):
        raise StockInfoFormatError(f'股票列表返回格式错误，需要List[dict], 实际是{type(rst)}')
    if not rst:
        raise StockInfoEmptyError(f'股票列表返回值的List为空')
    if not all((isinstance(item, dict)) for item in rst):
        invalid_items = [item for item in rst if not isinstance(item, dict)]
        raise StockInfoFormatError(f'股票列表返回值的List，内部需要是dict，实际是{type(invalid_items[0])}')
    if not all(REQUIRED_FIELDS_SET.issubset(d) for d in rst):
        invalid_keys = [d for d in rst if not REQUIRED_FIELDS_SET.issubset(d)]
        raise StockInfoFieldError(f'股票列表返回值的List，内部dict的字段应该至少包含:{REQUIRED_FIELDS_SET}，实际是{invalid_keys[0].keys()}')
    
    rst = [{'code': item['dm'].split('.')[0], 'name': item['mc'], 'exchange': item['jys']} for item in rst]
    return rst

def _handle_error()->pd.DataFrame:
    '''
    处理异常  
    
    查询security_info.db中的stock_info表，返回原来的表数据
    '''
    fallback_df = stock_info.get_all_stock_info()
    return fallback_df

def fetch_and_clean()->Tuple[pd.DataFrame, Counter]:
    '''
    获取股票列表信息并清洗  
    
    - 返回
        - pd.DataFrame: 股票列表信息
        - Counter: 兜底记录
    '''
    records = Counter()
    final_fallback_df = pd.DataFrame(
        {
            'code': ['888888'],
            'name': ['未知股票'],
            'exchange': ['未知交易所'],
            'last_update_date': [dt.date.today().strftime('%Y-%m-%d')],
        }
    )

    try:
        rst = fetch()
        df = pd.DataFrame(rst)
        df['last_update_date'] = dt.date.today().strftime('%Y-%m-%d') 
    except Exception as e:
        try:
            df = _handle_error()
            records[_FALLBACK_KEY_ORIGINAL_TABLE] += 1
        except Exception as e:
            try:
                logger.exception(f'原始表兜底查询失败: 启用最终逻辑：code=888888, last_update_date=today，请及时处理')
                df = final_fallback_df
                records[_FALLBACK_KEY_FINAL] += 1
            except Exception as e:
                logger.exception(f'最终逻辑兜底查询失败: 启用最终逻辑：code=888888, last_update_date=today，请及时处理')
                df = final_fallback_df
                records[_FALLBACK_KEY_FINAL] += 1
               
    
    try:
        validate(df, STOCK_INFO_SCHEMA)
    except Exception:
        logger.exception('校验失败，采用兜底：code=888888, last_update_date=today，请及时处理')
        df = final_fallback_df
        records[_FALLBACK_KEY_VALIDATE] += 1

    return df, records

def provide()->Tuple[pd.DataFrame, Counter, int]:
    '''
    提供股票列表信息
    
    - 返回
        - pd.DataFrame: 股票列表信息
        - Counter: 兜底记录
        - int: 更新时间
    '''
    # 总次数计数器
    total_fetch_times = 0
    total_fallback_records = Counter()

    # 获取数据与兜底记录
    df, fallback_records = fetch_and_clean()
    total_fallback_records.update(fallback_records)
    total_fetch_times += 1

    # 返回数据与总兜底记录
    return df, total_fallback_records, total_fetch_times