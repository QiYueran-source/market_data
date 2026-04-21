'''
从麦蕊智数获取ETF日线数据

更新时间：实时，可在收盘后更新  
限流：300次/min  

rl: https://api.mairuiapi.com/fd/real/time/基金代码(如159001)/您的licence

返回示例：
{"pe":0,"ud":-0.002,"pc":-0.002,"zf":0.002,"p":99.998,"o":100,"h":100,"l":99.998,"yc":100,"cje":340180600,"v":34018,"pv":3401832,"tv":2,"t":"2026-04-07 11:04:36"}：

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
etf_daily_trade_data_<code>
|字段|类型|注释|主键|最终兜底值|
|----|----|----|----|----|
|code|TEXT|ETF代码，如 159718 (无后缀) |True|提供的code|
|trade_date|TEXT|交易时间，格式为yyyy-mm-dd|True|当前日期|
|open|REAL|开盘价(元)|False|0.0|
|high|REAL|最高价(元)|False|0.0|
|low|REAL|最低价(元)|False|0.0|
|close|REAL|收盘价(元)|False|0.0|
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


# 工具
from providers.provider_utils import limit, retry
from models.table_schema import validate
from schema.daily_trade_data import ETF_DAILY_TRADE_DATA_SCHEMA
from db.api.security_info import etf_info

# 环境变量
from dotenv import load_dotenv
load_dotenv()
MAIRUI_TOKEN = os.getenv('MAIRUI_TOKEN')

# URL  
MAIRUI_DAILY_TRADE_DATA_URL = 'https://api.mairuiapi.com/fd/real/time'

# 规定字段
REQUIRED_FIELDS_SET = {'o', 'h', 'l', 'p'}
OTHER_FIELDS_SET = {'pe', 'ud', 'pc', 'zf', 'yc', 'cje', 'v', 'pv', 'tv', 't'}
OPTIONAL_DEFAULTS_MAP = {
    'pe': 0.0,
    'ud': 0.0,
    'pc': 0.0,
    'zf': 0.0,
    'yc': 0.0,
    'cje': 0.0,
    'v': 0,
    'pv': 0,
    'tv': 0.0,
    't': '',
}

# 兜底记录
_FALLBACK_KEY_FINAL = 'FETCH_FAIL_USE_FALLBACK_ZERO' # 用一个888888_today代码兜底
_FALLBACK_KEY_VALIDATE = 'VALIDATE_FAIL_USE_FALLBACK_ZERO' # 校验失败，用一个888888_today代码兜底

# 最新ETF列表
LATEST_ETF_LIST = etf_info.get_latest_etf_list()

# 日志
from utils.logs import get_logger
logger = get_logger('etf_daily_trade_data_by_mairui')

# 异常
from exceptions.api_error.base_error import NotFoundError, BadRequestError
from exceptions.api_error.mairui_error import (
    MairuiTokenEmptyError,
    MairuiQuotaExhaustedError,
    InsufficientTierError,
    InvalidLicenceError,
    DailyTradeDataJsonDecodeError,
    DailyTradeDataFormatError,
    DailyTradeDataEmptyError,
    DailyEtfNotInLatestListError
)

# 获取ETF日线数据
@retry((BadRequestError))
@limit('mairui')
def fetch(code:str)->Dict[str, Any]:
    '''
    获取ETF分钟交易数据
    '''
    if code not in LATEST_ETF_LIST:
        # 抛出，交给fetch_and_clean处理
        raise DailyEtfNotInLatestListError(f'代码{code}不在最新ETF列表中')

    url = f'{MAIRUI_DAILY_TRADE_DATA_URL}/{code}/{MAIRUI_TOKEN}'
    if not MAIRUI_TOKEN:
        raise MairuiTokenEmptyError('麦蕊智数TOKEN未设置')
    try:
        response = requests.get(url)
        status_code = response.status_code
        if status_code == 404:
            raise NotFoundError(f'{MAIRUI_DAILY_TRADE_DATA_URL} URL不存在，状态码: {status_code}')
        if status_code == 503:
            raise MairuiQuotaExhaustedError(f'{MAIRUI_DAILY_TRADE_DATA_URL} 请求次数超过限额，状态码: {status_code}')
        if status_code == 101:
            raise InsufficientTierError(f'{MAIRUI_DAILY_TRADE_DATA_URL} Token等级不足，状态码: {status_code}')
        if status_code == 102:
            raise InvalidLicenceError(f'{MAIRUI_DAILY_TRADE_DATA_URL} licence无效，状态码: {status_code}')
        if status_code != 200:
            raise BadRequestError(f'{MAIRUI_DAILY_TRADE_DATA_URL} 返回了错误的状态码: {status_code}')
    except requests.exceptions.RequestException as e:
        raise BadRequestError(f'请求麦蕊智数API失败: {e}')

    try:
        rst = response.json()
    except json.JSONDecodeError as e:
        raise DailyTradeDataJsonDecodeError(f'分钟交易数据返回不是合法json: {e}')

    if not isinstance(rst, dict):
        raise DailyTradeDataFormatError(f'分钟交易数据返回格式错误，需要dict，实际是{type(rst)}')
    if not rst:
        raise DailyTradeDataEmptyError(f'分钟交易数据返回值为空')
    
    # 校验必填字段
    missing_required = sorted(REQUIRED_FIELDS_SET - set(rst.keys()))
    if missing_required:
        raise DailyTradeDataFormatError(
            f'日线数据缺少必填字段: {missing_required}，实际字段: {sorted(rst.keys())}'
        )

    # 校验可选字段
    missing_optional = sorted(OTHER_FIELDS_SET - set(rst.keys()))
    if missing_optional:
        logger.warning(
            'ETF日线数据选填字段缺失，etf_code=%s，missing=%s，将使用默认值',
            code,
            missing_optional,
        )

    for field, default_value in OPTIONAL_DEFAULTS_MAP.items():
        rst.setdefault(field, default_value)
    return rst

# 获取ETF日线数据并清洗
def fetch_and_clean(code:str)->Tuple[pd.DataFrame, Counter]:
    '''
    获取ETF日线数据并清洗
    '''
    records = Counter()
    final_fallback_df = lambda code: pd.DataFrame(
        {
            'code': [code],
            'trade_date': [dt.date.today().strftime('%Y-%m-%d')],
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

    try:
        # 获取数据
        rst = fetch(code)
        trade_date = rst.get('t')
        if not trade_date:
            trade_date = dt.date.today().strftime('%Y-%m-%d')
        if isinstance(trade_date, dt.datetime):
            trade_date = trade_date.strftime('%Y-%m-%d')
        if isinstance(trade_date, str):
            trade_date = dt.datetime.strptime(trade_date, '%Y-%m-%d %H:%M:%S').date().strftime('%Y-%m-%d')

        # 转为df
        df = pd.DataFrame(
            {
                'code': [str(code)],
                'trade_date': [trade_date],
                'open': [float(rst['o'])],
                'high': [float(rst['h'])],
                'low': [float(rst['l'])],
                'close': [float(rst['p'])],
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
        )
    except DailyEtfNotInLatestListError as e:
        # 跳过，记警告
        logger.warning(f'ETF代码{code}不在最新ETF列表中，跳过: {e}')
        return pd.DataFrame(), records
    except Exception as e:
        logger.exception(f'API 拉取失败，etf_code={code}，进入兜底逻辑')
        df = final_fallback_df(code)
        records[_FALLBACK_KEY_FINAL] += 1
    
    # 验证df
    try:
        validate(df, ETF_DAILY_TRADE_DATA_SCHEMA)
    except Exception:
        logger.exception(f'校验失败，采用兜底：etf_code={code}，请及时处理')
        df = final_fallback_df(code)
        records[_FALLBACK_KEY_VALIDATE] += 1
    return df, records


# 提供ETF日线数据
def provide(codes:List[str])->Tuple[pd.DataFrame, Counter, int]:
    '''
    提供ETF日线数据

    - codes: 证券代码列表
    - return:
        - df: 日线数据DataFrame
        - total_fallback_records: 兜底记录，key:兜底原因，value:兜底次数
        - total_fetch_times: 总获取次数
    '''
    # 初始化
    comb_df = None
    total_fetch_times = 0
    total_fallback_records = Counter()

    # 多线程获取数据
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_and_clean, code) for code in codes]
        results = [future.result() for future in futures]
    
    # 合并数据
    for df, records in results:
        if df.empty:
            continue
        if comb_df is None:
            comb_df= df 
        else:
            comb_df = pd.concat([comb_df, df])
        total_fallback_records.update(records)
        total_fetch_times += 1
    # 返回
    return comb_df, total_fallback_records, total_fetch_times
    
    