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

# ---------------- etf复权因子 ----------------
class TushareETFAdjustmentFactorError(TushareError):
    '''TuShare ETF复权因子错误'''

class TushareETFAdjustmentDataFormatError(TushareETFAdjustmentFactorError):
    '''TuShare ETF复权因子数据格式错误'''