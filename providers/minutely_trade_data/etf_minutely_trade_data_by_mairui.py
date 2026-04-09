'''
从麦蕊智数获取ETF分钟交易数据  

更新时间：实时  
限流：300次/min  

url: https://api.mairuiapi.com/fd/real/time/基金代码(如159001)/您的licence

返回示例：
{"pe":0,"ud":-0.002,"pc":-0.002,"zf":0.002,"p":99.998,"o":100,"h":100,"l":99.998,"yc":100,"cje":340180600,"v":34018,"pv":3401832,"tv":2,"t":"2026-04-07 11:04:36"}

字段说明：
|字段|说明|
|----|----|
|pe|市盈率 % 注意 / 100 转换为无量纲|
|ud|涨跌额 元|
|pc|涨跌率 %|
|zf|振幅 %|
|p|当前价格 元|
|o|开盘价 元|
|h|最高价 元|
|l|最低价 元|
|yc|昨收价 元|
|cje|成交额 元|
|v|成交量 手 注意 * 100 转换为股|
|pv|原始成交量 股|
|tv|成交量（不知是什么）|
|t|交易时间 格式为yyyy-mm-dd hh:mm:ss|

库表结构：
minutely_trade_data_<code>
|字段|类型|注释|主键|最终兜底值|
|----|----|----|----|----|
|trade_datetime|TEXT|交易时间 格式为yyyy-mm-dd hh:mm:ss|True|当前时间|
|price|REAL|交易价格(元)|False|0.0|
|volume|INTEGER|交易量(股)|False|0.0|
|amount|REAL|交易金额(元)|False|0.0|
|original_volume|INTEGER|原始交易量(股)|False|0.0|
|yesterday_close_price|REAL|昨收价(元)|False|0.0|
|up_down|REAL|相对昨收盘涨跌额(元)|False|0.0|
|up_down_rate|REAL|相对昨收盘涨跌率|False|0.0|
|amplitude|REAL|振幅|False|0.0|
|turnover_rate|REAL|换手率|False|0.0|
|pe_ratio|REAL|市盈率|False|0.0|
'''
# 库
import os
import json
import datetime as dt 
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple, Any, Literal
from collections import Counter
from dotenv import load_dotenv
from sqlalchemy.event import listen
load_dotenv()

# 工具
from models.table_schema import TableSchema,validate
from providers.provider_utils import limit, retry

# 表结构
from schema.minutely_trade_data import (
    ETF_CODE_SCHEMA_MAP
)

# 环境变量
MAIRUI_TOKEN = os.getenv('MAIRUI_TOKEN')
MAIRUI_MINUTELY_TRADE_DATA_URL = 'https://api.mairuiapi.com/fd/real/time'

# 兜底记录
_FALLBACK_KEY_FINAL = 'ETF_USE_FALLBACK_ZERO' # 用兜底数据0兜底
_FALLBACK_KEY_VALIDATE = 'ETF_VALIDATE_FAIL_USE_FALLBACK_ZERO' # 校验失败，用兜底数据0兜底

# 日志
import logging
logger = logging.getLogger('minutely_trade_data.etf_minutely_trade_data_by_mairui')

# 异常
from exceptions.api_error.base_error import NotFoundError, BadRequestError
from exceptions.api_error.mairui_error import (
    MairuiTokenEmptyError,
    MairuiQuotaExhaustedError,
    InsufficientTierError,
    InvalidLicenceError,
    MinutelyTradeDataJsonDecodeError,
    MinutelyTradeDataFormatError,
    MinutelyTradeDataEmptyError,
    MinutelyEtfNotInLatestListError
)

# ETF列表
from db.api.security_info import etf_info
LATEST_ETF_LIST = etf_info.get_latest_etf_list()


@retry((BadRequestError))
@limit('mairui')
def fetch(code:str)->Dict[str, Any]:
    '''
    获取ETF分钟交易数据
    '''
    if code not in LATEST_ETF_LIST:
        # 抛出，交给fetch_and_clean处理
        raise MinutelyEtfNotInLatestListError(f'代码{code}不在最新ETF列表中')

    url = f'{MAIRUI_MINUTELY_TRADE_DATA_URL}/{code}/{MAIRUI_TOKEN}'
    try:
        response = requests.get(url)
        status_code = response.status_code
        if status_code == 404:
            raise NotFoundError(f'{MAIRUI_MINUTELY_TRADE_DATA_URL} URL不存在，状态码: {status_code}')
        if status_code == 503:
            raise MairuiQuotaExhaustedError(f'{MAIRUI_MINUTELY_TRADE_DATA_URL} 请求次数超过限额，状态码: {status_code}')
        if status_code == 101:
            raise InsufficientTierError(f'{MAIRUI_MINUTELY_TRADE_DATA_URL} Token等级不足，状态码: {status_code}')
        if status_code == 102:
            raise InvalidLicenceError(f'{MAIRUI_MINUTELY_TRADE_DATA_URL} licence无效，状态码: {status_code}')
        if status_code != 200:
            raise BadRequestError(f'{MAIRUI_MINUTELY_TRADE_DATA_URL} 返回了错误的状态码: {status_code}')
    except requests.exceptions.RequestException as e:
        raise BadRequestError(f'请求麦蕊智数API失败: {e}')

    try:
        rst = response.json()
    except json.JSONDecodeError as e:
        raise MinutelyTradeDataJsonDecodeError(f'分钟交易数据返回不是合法json: {e}')

    if not isinstance(rst, dict):
        raise MinutelyTradeDataFormatError(f'分钟交易数据返回格式错误，需要dict，实际是{type(rst)}')
    if not rst:
        raise MinutelyTradeDataEmptyError(f'分钟交易数据返回值为空')
    if not all(key in rst for key in ['pe', 'ud', 'pc', 'zf', 'p', 'o', 'h', 'l', 'yc', 'cje', 'v', 'pv', 'tv', 't']):
        raise MinutelyTradeDataFormatError(f'分钟交易数据返回值的dict，字段应该为:pe, ud, pc, zf, p, o, h, l, yc, cje, v, pv, tv, t，实际是{rst.keys()}')
    return rst

def fetch_and_clean(code:str) -> Tuple[str, pd.DataFrame, Counter]:
    '''
    获取分钟交易数据并清洗
    '''
    records = Counter()
    final_fallback_df = pd.DataFrame(
        {
            'trade_datetime': [dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'price': [0.0],
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
    
    try:
        rst = fetch(code)
        
        # 单独处理交易时间
        trade_datetime = rst['t'] 
        if not trade_datetime:
            trade_datetime = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(trade_datetime, dt.datetime):
            trade_datetime = trade_datetime.strftime('%Y-%m-%d %H:%M:%S')
        rst = {
            'trade_datetime': [str(trade_datetime)],
            'price': [float(rst['p'])],
            'volume': [int(rst['v'] * 100)],
            'amount': [float(rst['cje'])],
            'original_volume': [int(rst['pv'])],
            'yesterday_close_price': [float(rst['yc'])],
            'up_down': [float(rst['ud'])],
            'up_down_rate': [float(rst['pc'] / 100)],
            'amplitude': [float(rst['zf'] / 100)],
            'turnover_rate': [float(rst['tv'] / 100)],
            'pe_ratio': [float(rst['pe'] / 100)],
        }
        df = pd.DataFrame(rst)
    except MinutelyEtfNotInLatestListError as e:
        # 跳过，记警告
        logger.warning(f'ETF代码{code}不在最新ETF列表中，跳过: {e}')
        return code, pd.DataFrame(), records
    except Exception as e:
        logger.exception(f'API 拉取失败，etf_code={code}，进入兜底逻辑')
        df = final_fallback_df
        records[_FALLBACK_KEY_FINAL] += 1

    # 验证df
    try:
        validate(df, ETF_CODE_SCHEMA_MAP[code])
    except Exception:
        logger.exception(f'校验失败，采用兜底：etf_code={code}，请及时处理')
        df = final_fallback_df
        records[_FALLBACK_KEY_VALIDATE] += 1
    return code, df, records


def provide(codes:List[str])->Tuple[Dict[str, pd.DataFrame], Counter, int]:
    '''
    提供ETF分钟交易数据
    
    codes: 证券代码列表
    
    return:
    - dfs: 证券代码-DataFrame映射
    - total_fallback_records: 兜底记录
    - total_fetch_times: 总获取次数
    '''
    dfs = {}
    total_fallback_records = Counter()
    total_fetch_times = 0
    
    with ThreadPoolExecutor(max_workers=len(codes)) as executor:
        futures = [executor.submit(fetch_and_clean, code) for code in codes]
        for future in futures:
            code, df, fallback_records = future.result()
            if df.empty:
                continue
            dfs[code] = df
            total_fallback_records.update(fallback_records)
            total_fetch_times += 1
    return dfs, total_fallback_records, total_fetch_times
     

