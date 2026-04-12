'''
麦蕊智数API错误
'''
from exceptions.api_error.base_error import ApiError

class MairuiError(ApiError):
    '''麦蕊智数API错误基类'''

class MairuiTokenEmptyError(MairuiError):
    '''麦蕊智数TOKEN未设置'''

class MairuiQuotaExhaustedError(MairuiError):
    '''麦蕊智数请求次数超过限额，503状态码'''

class InsufficientTierError(MairuiError):
    '''麦瑞Token等级不足异常，101状态码'''

class InvalidLicenceError(MairuiError):
    '''麦蕊智数licence无效，102状态码'''

# -------------------- etf列表 --------------------
class EtfListJsonDecodeError(MairuiError):
    '''etf返回不是合法json'''

class EtfListFormatError(MairuiError):
    '''etf列表返回格式错误：不是List[dict]'''

class EtfFieldError(MairuiError):
    '''etf列表返回值的List，内部dict的字段应该为:dm, mc, jys'''

# -------------------- etf分钟交易数据 --------------------
class MinutelyTradeDataError(MairuiError):
    '''分钟交易数据错误基类'''

class MinutelyEtfNotInLatestListError(MinutelyTradeDataError):
    '''ETF代码不在最新ETF列表中'''

class MinutelyTradeDataJsonDecodeError(MinutelyTradeDataError):
    '''分钟交易数据返回不是合法json'''

class MinutelyTradeDataFormatError(MinutelyTradeDataError):
    '''分钟交易数据返回格式错误：不是dict'''

class MinutelyTradeDataEmptyError(MinutelyTradeDataError):
    '''分钟交易数据返回值为空'''

# -------------------- etf日线交易数据 --------------------
class DailyTradeDataError(MairuiError):
    '''日线交易数据错误基类'''

class DailyEtfNotInLatestListError(DailyTradeDataError):
    '''ETF代码不在最新ETF列表中'''

class DailyTradeDataJsonDecodeError(DailyTradeDataError):
    '''分钟交易数据返回不是合法json'''

class DailyTradeDataFormatError(DailyTradeDataError):
    '''分钟交易数据返回格式错误：不是dict'''

class DailyTradeDataEmptyError(DailyTradeDataError):
    '''分钟交易数据返回值为空'''

# -------------------- 股票列表 --------------------
class StockInfoError(MairuiError):
    '''股票列表错误基类'''

class StockInfoJsonDecodeError(StockInfoError):
    '''股票列表返回不是合法json'''

class StockInfoFormatError(StockInfoError):
    '''股票列表返回格式错误：不是List[dict]'''

class StockInfoEmptyError(StockInfoError):
    '''股票列表返回值为空'''

class StockInfoFieldError(StockInfoError):
    '''股票列表返回值的List，内部dict的字段应该为:dm, mc, jys'''