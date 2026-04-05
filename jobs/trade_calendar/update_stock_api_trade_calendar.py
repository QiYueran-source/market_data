'''
更新stock_api_trade_calendar表任务  

更新时间：早上9:00    
限流：40次/min  

流程：  
- 使用trade_calendar_by_stock_api.provide()获取数据
- 使用buffer写入db
'''
# 库
import datetime as dt

# schema, provider和buffer  
from schema.trade_calendar import STOCKAPI_TRADE_CALENDAR_SCHEMA
from providers.trade_calendar import trade_calendar_by_stock_api
from storage.buffer import Buffer

# 异常
from exceptions.api_error.base_error import ApiError
from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError

# 日志
from utils import get_logger
logger = get_logger('update_stock_api_trade_calendar_job')

# 缓存
stock_api_trade_calendar_buffer = Buffer(
    schema=STOCKAPI_TRADE_CALENDAR_SCHEMA,
    buffer_size=1
)

# 执行入口
def run():
    today = dt.date.today()
    try:
        df = trade_calendar_by_stock_api.provide(today)
        stock_api_trade_calendar_buffer.append(df)
        stock_api_trade_calendar_buffer.flush()
    except ApiError:
        logger.exception('API 请求失败')
        raise
    except ValidError:
        logger.exception('校验失败，未写入缓存')
        raise
    except BufferWriteError:
        logger.exception('写入数据库失败')
        raise
    except Exception:
        logger.exception('未预期错误')
        raise