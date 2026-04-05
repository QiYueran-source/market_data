from exceptions.api_error.base_error import ApiError

class StockApiError(ApiError):
    '''stock_api错误基类'''

# -------------------- 交易日历 --------------------
# ---- 交易日历API ----
class TradeCalendarError(StockApiError):
    '''交易日历错误基类'''

class StockApiQuotaExhaustedError(TradeCalendarError):
    '''请求次数超过限额'''

class UnexpectedApiCodeError(TradeCalendarError):
    '''返回了意外的API码'''

class DataEmptyError(TradeCalendarError):
    '''数据为空'''

class WrongDataError(TradeCalendarError):
    '''数据格式错误'''

class WrongIsOpenRangeError(TradeCalendarError):
    '''is_open范围错误'''

# ---- 兜底 ----
class FallBackError(TradeCalendarError):
    '''兜底错误基类'''

class SQLiteError(FallBackError):
    '''兜底时连接sqlite失败'''

class FallBackDataEmptyError(FallBackError):
    '''兜底时数据为空'''
