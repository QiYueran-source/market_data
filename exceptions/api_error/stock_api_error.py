from exceptions.api_error.base_error import ApiError

# -------------------- stock_api --------------------
class StockApiError(ApiError):
    '''stock_api错误基类'''

class StockApiQuotaExhaustedError(StockApiError):
    '''请求次数超过限额'''

class UnexpectedApiCodeError(StockApiError):
    '''返回了意外的API码'''

class DataEmptyError(StockApiError):
    '''数据为空'''

class WrongDataError(StockApiError):
    '''数据格式错误'''

class WrongIsOpenRangeError(StockApiError):
    '''is_open范围错误'''
