'''
更新时间：每天下午17:00
限流：300次/min
'''
# 库
import math
import datetime as dt
from collections import Counter

# 工具
from models.job_info import JobInfo
from db.api.security_info import etf_info
from db.api.trade_calendar import stock_api_trade_calendar

# schema
from schema.daily_trade_data import ETF_DAILY_TRADE_DATA_SCHEMA

# 提供者
from providers.daily_trade_data import etf_daily_trade_data_by_mairui

# 缓存
BATCH_SIZE = 500
from storage.buffer import Buffer
etf_daily_trade_data_buffer = Buffer(
    schema = ETF_DAILY_TRADE_DATA_SCHEMA,
    buffer_size = BATCH_SIZE * 2,
)

# etf列表
ETF_CODE_LIST = etf_info.get_latest_etf_list()

# 日志
from utils import get_logger
logger = get_logger('update_etf_daily_trade_data_job')

# 异常
from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError

# 条件
CONDITION = stock_api_trade_calendar.is_trade_date(dt.date.today())

def run()->JobInfo:
    '''
    执行入口  
    
    逻辑：
    获取最新更新日期，如果：  
        - 距离上次更新超过 UPDATE_INTERVAL 天  
        - 处于非交易日  
    则更新
    '''
    job_name = 'update_etf_daily_trade_data'
    total_fallback_records = Counter()
    total_fetch_times = 0
    success = True
    error = None
    write_times = 0
    write_failed_times = 0
    rounds_count = 0 # 轮次计数

    # 条件不满足，仅返回JobInfo信息
    if not CONDITION:
        info:JobInfo = {
            'job_name': job_name,
            'finished_at': None,
            'success': None,
            'error': None,
            'write_times': None,
            'write_failed_times': None,
            'total_fetch_times': None,
            'fallback_records': None,
            'additional_info': {
                '消息':'未满足更新条件',
                '是否为交易日': '是' if CONDITION else '否'}
            }
        return info

    # 条件满足，开始更新
    # 拆分代码
    n = len(ETF_CODE_LIST)
    num_batches = math.ceil(n / BATCH_SIZE) if n else 0

    # 更新
    try:
        for batch_idx in range(num_batches):
            # 获取代码
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, n)
            codes = ETF_CODE_LIST[start_idx:end_idx]
            
            # 获取数据
            df, fallback_records, fetch_times = etf_daily_trade_data_by_mairui.provide(codes)
            
            # 更新
            flushed = etf_daily_trade_data_buffer.append(df)
            if flushed:
                write_times += 1
            total_fallback_records.update(fallback_records)
            rounds_count += 1
            total_fetch_times += fetch_times
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
            job_name=job_name,
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
        flushed = etf_daily_trade_data_buffer.flush()
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
            job_name=job_name,
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
    
    # 返回结果
    info = JobInfo(
        job_name=job_name,
        finished_at=dt.datetime.now(),
        success=success,
        error=error,
        write_times=write_times,
        write_failed_times=write_failed_times,
        total_fetch_times=total_fetch_times,
        fallback_records=dict(total_fallback_records),
        additional_info={'消息': '更新ETF每日交易数据成功', '轮次': rounds_count}
    )
    return info
