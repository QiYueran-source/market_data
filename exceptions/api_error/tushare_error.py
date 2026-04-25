'''
TuShare API错误  
'''
from exceptions.api_error.base_error import ApiError

class TushareError(ApiError):
    '''TuShare API错误基类'''

class TushareQuotaExhaustedError(TushareError):
    '''TuShare API请求超过限额'''

class TushareTokenError(TushareError):
    '''TuShare APIToken错误'''

class TushareProClientError(TushareError):
    '''TuShare API客户端错误'''

# ---------------- etf复权因子 ----------------
class TushareETFExchangeNotFoundError(TushareError):
    '''TuShare ETF交易所未找到'''

class TushareETFAdjustmentFactorError(TushareError):
    '''TuShare ETF复权因子错误'''

class TushareETFAdjustmentDataFormatError(TushareETFAdjustmentFactorError):
    '''TuShare ETF复权因子数据格式错误'''

# ---------------- 股票日线（pro_bar） -----------------
class TushareStockDailyError(TushareError):
    '''TuShare 股票日线（pro_bar）链路错误基类'''

class TushareStockDailyProBarError(TushareStockDailyError):
    '''TuShare pro_bar 调用失败或接口返回错误'''

class TushareStockExchangeNotFoundError(TushareStockDailyError):
    '''TuShare 股票交易所未找到'''

class TushareStockDailyEmptyError(TushareStockDailyError):
    '''TuShare 股票日线返回空结果'''


class TushareStockDailyFormatError(TushareStockDailyError):
    '''TuShare 股票日线返回缺列、列类型或格式不符合预期'''


class TushareStockNotInListError(TushareStockDailyError):
    '''股票代码不在当前 stock_info 最新列表中'''


# ---------------- 股票复权因子 -----------------
class TushareStockAdjustmentFactorError(TushareError):
    '''TuShare 股票复权因子链路错误基类'''


class TushareStockAdjustmentDataFormatError(TushareStockAdjustmentFactorError):
    '''TuShare 股票复权因子数据格式错误'''


class TushareStockAdjustmentExchangeNotFoundError(TushareStockAdjustmentFactorError):
    '''TuShare 股票复权因子场景下股票交易所未找到'''
