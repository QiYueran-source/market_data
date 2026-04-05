'''
从stock_api获取交易日历数据  

更新时间：早上9:00  
限流：40次/min  
'''
# 引入库
import json
import datetime as dt
import requests
from providers.provider_utils import *

# 异常
from exceptions.api_error.base_error import BadRequestError, NotFoundError
from exceptions.api_error.stock_api_error import StockApiQuotaExhaustedError, UnexpectedApiCodeError, DataEmptyError, WrongDataError, WrongIsOpenRangeError

# 获取变量的
STOCKAPI_TRADE_CALENDAR_URL = "https://www.stockapi.com.cn/v1/base/tradeDate"
_STOCKAPI_SUCCESS_CODE = 20000
_STOCKAPI_QUOTA_CODE = 88886
_REQUEST_TIMEOUT_SEC = 30

@retry((UnexpectedApiCodeError,DataEmptyError,WrongDataError,WrongIsOpenRangeError))
@limit('stock_api_trade_calendar')
def fetch() -> int:
    '''返回今天是否是交易日'''
    try:
        response = requests.get(
            STOCKAPI_TRADE_CALENDAR_URL,
            params = {'tradeDate': dt.datetime.now().date().strftime('%Y-%m-%d')},
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
