'''
更新ETF复权因子

更新时间：每天收盘后 17:00 
限流：未知，用tushare通用限流器即可，单次限2000条  
'''
# 库
import datetime as dt
from collections import Counter

# 工具
from models.job_info import JobInfo
from db.api.trade_calendar import stock_api_trade_calendar

# 表结构
from schema.adjustment_factor import ETF_ADJUSTMENT_FACTOR_SCHEMA

# 提供者
from providers.adjustment_factor.etf_adjustment_factor_by_tushare import provide

# 缓存
from storage.buffer import Buffer
etf_adjustment_factor_buffer = Buffer(
    schema = ETF_ADJUSTMENT_FACTOR_SCHEMA,
    buffer_size = 1000,
)

# 日志
from utils import get_logger
logger = get_logger('update_stock_adjustment_factor_job')

# 异常
from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError

# 条件
CONDITION = stock_api_trade_calendar.is_trade_date(dt.date.today())

# 运行
def run()->JobInfo:
    '''
    运行
    '''
    job_name = 'update_stock_adjustment_factor'
    total_fallback_records = Counter()
    total_fetch_times = 0
    success = True
    error = None
    write_times = 0
    write_failed_times = 0

    # 条件不满足，仅返回JobInfo信息
    if not CONDITION:
        info:JobInfo = JobInfo(
            job_name = job_name,
            finished_at = None,
            success = None,
            error = None,
            write_times = None,
            write_failed_times = None,
            total_fetch_times = None,
            fallback_records = None,
            additional_info = {
                '消息': '未满足更新条件',
                '是否为交易日': '是' if CONDITION else '否'}
        )
        return info
    
    # 条件满足，开始更新
    try:
        df, fallback_records, fetch_times = provide()
        total_fallback_records.update(fallback_records)
        total_fetch_times += fetch_times
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
        info = JobInfo(
            job_name = job_name,
            finished_at = dt.datetime.now(),
            success = success,
            error = error,
            write_times = write_times,
            write_failed_times = write_failed_times,
            total_fetch_times = total_fetch_times,
            fallback_records = dict(total_fallback_records),
            additional_info = {
                '消息': 'provide过程中遇到未预期错误，未写入缓存',
            }
        )
        return info
    
    # 更新缓存
    try:
        flushed = etf_adjustment_factor_buffer.append(df)
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
            job_name = job_name,
            finished_at = dt.datetime.now(),
            success = success,
            error = error,
            write_times = write_times,
            write_failed_times = write_failed_times,
            total_fetch_times = total_fetch_times,
            fallback_records = dict(total_fallback_records),
            additional_info = {
                '消息': 'append过程中遇到未预期错误，未写入缓存'
            }
        )
        return info
        
    # 最后flush缓存
    try:
        flushed = etf_adjustment_factor_buffer.flush()
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
            job_name = job_name,
            finished_at = dt.datetime.now(),
            success = success,
            error = error,
            write_times = write_times,
            write_failed_times = write_failed_times,
            total_fetch_times = total_fetch_times,
            fallback_records = dict(total_fallback_records),
            additional_info = {
                '消息': 'flush过程中遇到未预期错误，未写入数据库'
            }
        )
        return info
    
    info = JobInfo(
        job_name = job_name,
        finished_at = dt.datetime.now(),
        success = success,
        error = error,
        write_times = write_times,
        write_failed_times = write_failed_times,
        total_fetch_times = total_fetch_times,
        fallback_records = dict(total_fallback_records),
        additional_info = {
            '消息': '更新ETF复权因子成功'
        }
    )
    return info