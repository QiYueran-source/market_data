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

class FieldError(MairuiError):
    '''etf列表返回值的List，内部dict的字段应该为:dm, mc, jys'''