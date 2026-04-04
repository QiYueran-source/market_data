'''
API错误  

这是最重要的一类错误，需要和API的返回/接口对应  

- StockApiError: stock_api的错误
    - 
'''
# 基类
class ApiError(Exception):
    '''API错误基类'''

class NotFoundError(ApiError):
    '''
    未找到错误，
    这是一个通用的错误，通常表示API地址错误或者被移除了
    '''

# -------------------- stock_api --------------------
class StockApiError(ApiError):
    '''stock_api错误基类'''

class StockApiQuotaExhaustedError(StockApiError):
    '''请求次数超过限额'''

