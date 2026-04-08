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
from models.job_info import JobInfo

# 异常
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
    # JobInfo字段 
    total_fallback_records = Counter()
    total_fetch_times = 0
    success = True
    error = None
    write_times = 0
    write_failed_times = 0
    
    # provide数据
    try:
        df, fallback_records, fetch_times = trade_calendar_by_stock_api.provide(dt.date.today())
        total_fallback_records.update(fallback_records)
        total_fetch_times += fetch_times
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
        info = JobInfo(
            job_name='update_stock_api_trade_calendar',
            finished_at=dt.datetime.now(),
            success=success,
            error=error,
            write_times=write_times,
            write_failed_times=write_failed_times,
            total_fetch_times=total_fetch_times,
            fallback_records=dict(total_fallback_records),
            additional_info={}
        )
        return info
    
    # 写入缓存
    try:
        flushed = stock_api_trade_calendar_buffer.append(df)
        if flushed:
            write_times += 1
    except ValidError as e:
        logger.exception('append到buffer过程中校验失败，未写入缓存')
    except BufferWriteError as e:
        write_times += 1
        write_failed_times += 1
        logger.exception('写入数据库失败')
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
        info = JobInfo(
            job_name='update_stock_api_trade_calendar',
            finished_at=dt.datetime.now(),
            success=success,
            error=error,
            write_times=write_times,
            write_failed_times=write_failed_times,
            total_fetch_times=total_fetch_times,
            fallback_records=dict(total_fallback_records),
            additional_info={'消息': 'append过程中遇到未预期错误，未写入缓存'}
        )
        return info

    # 最后flush缓存
    try:
        flushed = stock_api_trade_calendar_buffer.flush()
        if flushed:
            write_times += 1
    except BufferWriteError as e:
        write_times += 1
        write_failed_times += 1
        logger.exception('写入数据库失败')
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
        info = JobInfo(
            job_name='update_stock_api_trade_calendar',
            finished_at=dt.datetime.now(),
            success=success,
            error=error,
            write_times=write_times,
            write_failed_times=write_failed_times,
            total_fetch_times=total_fetch_times,
            fallback_records=dict(total_fallback_records),
            additional_info={'消息': 'flush过程中遇到未预期错误，未写入数据库'}
        )
        return info

    info:JobInfo = {
        'job_name': 'update_stock_api_trade_calendar',
        'finished_at': dt.datetime.now(),
        'success': success,
        'error': error,
        'write_times': write_times,
        'write_failed_times': write_failed_times,
        'total_fetch_times': total_fetch_times,
        'fallback_records': dict(total_fallback_records),
        'additional_info': {'消息': '更新交易日历成功'}
    }
    return info