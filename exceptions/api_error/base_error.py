# 基类
class ApiError(Exception):
    '''API错误基类'''

# -------------------- 通用错误(状态码错误) --------------------
class NotFoundError(ApiError):
    '''
    未找到错误，
    这是一个通用的错误，通常表示API地址错误或者被移除了
    '''

class BadRequestError(ApiError):
    '''
    请求错误，
    包括其他不同的状态码
    '''