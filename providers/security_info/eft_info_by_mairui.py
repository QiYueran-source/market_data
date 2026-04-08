'''
从 麦蕊智数 获取ETF信息    

更新时间：每天下午16：20  
限流：300次/min    

url: https://api.mairuiapi.com/fd/list/etf/您的licence

返回示例：
[{'dm': '159718', 'mc': '华安创业板50ETF', 'jys': '上海证券交易所'}, ... ]
'''
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
from schema.security_info import ETF_INFO_SCHEMA
from db.api.security_info import etf_info

# 环境变量
MAIRUI_TOKEN = os.getenv('MAIRUI_TOKEN')
MAIRUI_ETF_INFO_URL = 'https://api.mairuiapi.com/fd/list/etf/'

# 规定字段
REQUIRED_FIELDS_SET = {'dm', 'mc', 'jys'}

# 兜底记录
_FALLBACK_KEY_ORIGINAL_TABLE = 'FETCH_FAILED_USE_ORIGINAL_TABLE' # 失败后，用原来的info表兜底
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_CODE_888888_TODAY' # 用一个888888_today代码兜底
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_CODE_888888_TODAY' # 校验失败，用一个888888_today代码兜底

# 日志
import logging
logger = logging.getLogger('security_info.eft_info_by_mairui')

# 异常
from exceptions.api_error.base_error import NotFoundError, BadRequestError
from exceptions.api_error.mairui_error import (
    ApiError,
    MairuiTokenEmptyError,
    EtfListJsonDecodeError,
    EtfListFormatError,
    MairuiQuotaExhaustedError,
    InsufficientTierError,
    InvalidLicenceError,
    FieldError,
)

# 获取ETF信息
@retry((BadRequestError))
@limit('mairui')
def fetch()->List[Dict[str, str]]:
    '''
    获取ETF信息  
    
    - 抛出
        - MairuiTokenEmptyError: 麦蕊智数TOKEN未设置
        - BadRequestError: 请求麦蕊智数API失败
        - NotFoundError: {MAIRUI_ETF_INFO_URL} URL不存在
        - MairuiQuotaExhaustedError: {MAIRUI_ETF_INFO_URL} 请求次数超过限额
        - InsufficientTierError: {MAIRUI_ETF_INFO_URL} Token等级不足
        - InvalidLicenceError: {MAIRUI_ETF_INFO_URL} licence无效
        - FieldError: etf列表返回值的List，内部dict的字段应该至少包含:{REQUIRED_FIELDS_SET}
        - EtfListJsonDecodeError: etf列表返回不是合法json
        - EtfListFormatError: etf列表返回格式错误，需要List[dict], 实际是{type(rst)}
        - EtfListFormatError: etf列表返回值的List为空
        - EtfListFormatError: etf列表返回值的List，内部需要是dict，实际是{type(invalid_items[0])}
        - FieldError: etf列表返回值的List，内部dict的字段应该至少包含:{REQUIRED_FIELDS_SET}，实际是{invalid_keys[0].keys()}

    - 返回
        - list: ETF信息列表
            - dict: ETF信息
                - code: ETF代码
                - name: ETF名称
                - exchange: ETF所在交易所
    '''
    if not MAIRUI_TOKEN:
        raise MairuiTokenEmptyError('麦蕊智数TOKEN未设置')

    url = MAIRUI_ETF_INFO_URL + MAIRUI_TOKEN
    try:
        response = requests.get(url)
    except requests.exceptions.RequestException as e:
        raise BadRequestError(f'请求麦蕊智数API失败: {e}')
    
    status_code = response.status_code
    if status_code == 404:
        raise NotFoundError(f'{MAIRUI_ETF_INFO_URL} URL不存在，状态码: {status_code}')
    if status_code == 503:
        raise MairuiQuotaExhaustedError(f'{MAIRUI_ETF_INFO_URL} 请求次数超过限额，状态码: {status_code}')
    if status_code == 101:
        raise InsufficientTierError(f'{MAIRUI_ETF_INFO_URL} Token等级不足，状态码: {status_code}')
    if status_code == 102:
        raise InvalidLicenceError(f'{MAIRUI_ETF_INFO_URL} licence无效，状态码: {status_code}')
    if status_code != 200:
        raise BadRequestError(f'{MAIRUI_ETF_INFO_URL} 返回了错误的状态码: {status_code}')
    
    try:
        rst = response.json()
    except json.JSONDecodeError as e:
        raise EtfListJsonDecodeError(f'etf列表返回不是合法json: {e}')
    if not isinstance(rst, list):
        raise EtfListFormatError(f'etf列表返回格式错误，需要List[dict], 实际是{type(rst)}')
    if not rst:
        raise EtfListFormatError(f'etf列表返回值的List为空')
    if not all((isinstance(item, dict)) for item in rst):
        invalid_items = [item for item in rst if not isinstance(item, dict)]
        raise EtfListFormatError(f'etf列表返回值的List，内部需要是dict，实际是{type(invalid_items[0])}')
    if not all(REQUIRED_FIELDS_SET.issubset(d) for d in rst):
        invalid_keys = [d for d in rst if not REQUIRED_FIELDS_SET.issubset(d)]
        raise FieldError(f'etf列表返回值的List，内部dict的字段应该至少包含:{REQUIRED_FIELDS_SET}，实际是{invalid_keys[0].keys()}')
    
    rst = [{'code': item['dm'].split('.')[0], 'name': item['mc'], 'exchange': item['jys']} for item in rst]
    return rst

def _handle_error()->pd.DataFrame:
    '''
    处理异常  

    查询security_info.db中的etf_info表，返回原来的表数据
    '''
    fallback_df = etf_info.get_all_etf_info()
    return fallback_df

def fetch_and_clean()->Tuple[pd.DataFrame, Counter]:
    '''
    获取ETF信息并清洗
    '''
    records = Counter()
    last_update_date = dt.date.today().strftime('%Y-%m-%d')
    final_fallback_df = pd.DataFrame(
        {
            'code': ['888888'],
            'name': ['未知ETF'],
            'exchange': ['未知交易所'],
            'last_update_date': [last_update_date],
        }
    )
    try:
        rst = fetch()
        df = pd.DataFrame(rst)
        df['last_update_date'] = dt.date.today().strftime('%Y-%m-%d') 
    except ApiError as e:
        logger.exception('API 拉取失败，进入兜底逻辑')
        try:
            df = _handle_error()
            records[_FALLBACK_KEY_ORIGINAL_TABLE] += 1
        except Exception as e:
            logger.exception(f'兜底查询失败: 启用最终逻辑：code=888888, last_update_date=today，请及时处理')
            df = final_fallback_df
            records[_FALLBACK_KEY_FINAL] += 1
    except Exception as e:
        # 其他异常，交给上层job处理
        raise e
    
    # 验证df
    try:
        validate(df, ETF_INFO_SCHEMA)
    except Exception:
        logger.exception('校验失败，采用兜底：code=888888, last_update_date=today，请及时处理')
        df = final_fallback_df
        records[_FALLBACK_KEY_VALIDATE] += 1
    return df, records

def provide()->Tuple[pd.DataFrame, Counter, int]:
    '''
    提供ETF信息  

    返回：
    - pd.DataFrame: ETF信息
    - Counter: 兜底记录，key:兜底原因，value:兜底次数
    - int: 总获取次数 1次
    '''
    # 总兜底计数器，用于汇总所有兜底记录  
    provide_total_fallback_records = Counter()

    # 总次数计数器
    total_fetch_times = 0

    # 获取数据与兜底记录  
    df, fallback_records = fetch_and_clean()
    provide_total_fallback_records.update(fallback_records)
    total_fetch_times += 1

    # 返回数据与总兜底记录  
    return df, provide_total_fallback_records, total_fetch_times