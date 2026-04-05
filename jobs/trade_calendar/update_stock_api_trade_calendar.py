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
from collections import Counter

# schema, provider和buffer  
from schema.trade_calendar import STOCKAPI_TRADE_CALENDAR_SCHEMA
from providers.trade_calendar import trade_calendar_by_stock_api
from storage.buffer import Buffer

# job工具
from jobs.job_utils import JobInfo

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
def run()->JobInfo:
    '''
    执行入口

    返回：
    - JobInfo: 执行信息，用于邮件通知  
    '''
    total_fallback_records = Counter()
    total_fetch_times = 0
    today = dt.date.today()
    success = True
    error = None
    try:
        df, fallback_records, fetch_times = trade_calendar_by_stock_api.provide(today)
        total_fallback_records.update(fallback_records) # 汇总所有兜底记录  
        total_fetch_times += fetch_times # 汇总总获取次数
        stock_api_trade_calendar_buffer.append(df) # 写入缓存
        stock_api_trade_calendar_buffer.flush() # 刷新缓存
    except ApiError as e:
        logger.exception('API 请求失败')
        success = False
        error = e
    except ValidError as e:
        logger.exception('校验失败，未写入缓存')
        success = False
        error = e
    except BufferWriteError as e:
        logger.exception('写入数据库失败')
        success = False
        error = e
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
    finally:
        info:JobInfo = {
            'job_name': 'update_stock_api_trade_calendar',
            'finished_at': dt.datetime.now(),
            'success': success,
            'error': error,
            'total_fetch_times': total_fetch_times,
            'fallback_records': dict(total_fallback_records),
            'additional_info': {}
        }
        return info