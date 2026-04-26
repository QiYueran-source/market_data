'''
更新股票复权因子

更新时间：每天收盘后 17:00 
限流：未知，用tushare通用限流器即可，单次限2000条  
'''
# 库
import datetime as dt
import time
from collections import Counter
import pandas as pd

# 工具
from models.job_info import JobInfo
from db.api.trade_calendar import stock_api_trade_calendar
from db.api.security_info import stock_info

# 表结构
from schema.adjustment_factor import STOCK_ADJUSTMENT_FACTOR_SCHEMA

# 提供者
from providers.adjustment_factor.stock_adjustment_factor_by_tushare import provide

# 缓存
from storage.buffer import Buffer
stock_adjustment_factor_buffer = Buffer(
    schema = STOCK_ADJUSTMENT_FACTOR_SCHEMA,
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
BATCH_SIZE = 50
BATCH_SLEEP_SECONDS = 60.0
MAX_WORKERS = 50

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
        all_codes = stock_info.get_latest_stock_list()
        frames = []
        for idx in range(0, len(all_codes), BATCH_SIZE):
            batch_codes = all_codes[idx:idx + BATCH_SIZE]
            batch_df, fallback_records, fetch_times = provide(
                codes=batch_codes,
                max_workers=MAX_WORKERS,
            )
            if batch_df is not None and not batch_df.empty:
                frames.append(batch_df)
            total_fallback_records.update(fallback_records)
            total_fetch_times += fetch_times

            has_next_batch = idx + BATCH_SIZE < len(all_codes)
            if has_next_batch and BATCH_SLEEP_SECONDS > 0:
                logger.info(
                    '股票复权因子批次完成，休眠 %.1f 秒后继续，processed=%s/%s',
                    BATCH_SLEEP_SECONDS,
                    idx + len(batch_codes),
                    len(all_codes),
                )
                time.sleep(BATCH_SLEEP_SECONDS)

        if frames:
            df = pd.concat(frames, ignore_index=True)
        else:
            df = pd.DataFrame(columns=STOCK_ADJUSTMENT_FACTOR_SCHEMA.cols)
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
        flushed = stock_adjustment_factor_buffer.append(df)
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
        flushed = stock_adjustment_factor_buffer.flush()
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
            '消息': '更新股票复权因子成功'
        }
    )
    return info