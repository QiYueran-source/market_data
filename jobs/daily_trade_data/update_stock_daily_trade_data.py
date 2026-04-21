'''
更新股票日线（TuShare pro_bar，不复权）。

与 ETF 日线任务类似：交易日执行、分批、Buffer、JobInfo。
'''
# 库
import datetime as dt
import math
import os
from collections import Counter

# 工具
from models.job_info import JobInfo
from db.api.trade_calendar import stock_api_trade_calendar
from providers.daily_trade_data import stock_daily_trade_data_by_tushare
from schema.daily_trade_data import STOCK_DAILY_TRADE_DATA_SCHEMA
from storage.buffer import Buffer
from db.api.security_info import stock_info

BATCH_SIZE = int(os.getenv('STOCK_DAILY_JOB_BATCH_SIZE', '500'))
stock_daily_trade_data_buffer = Buffer(
    schema=STOCK_DAILY_TRADE_DATA_SCHEMA,
    buffer_size=BATCH_SIZE * 2,
)

from utils import get_logger
logger = get_logger('update_stock_daily_trade_data_job')

from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError
CONDITION = stock_api_trade_calendar.is_trade_date(dt.date.today())


def run() -> JobInfo:
    job_name = 'update_stock_daily_trade_data'
    total_fallback_records: Counter = Counter()
    total_fetch_times = 0
    success = True
    error = None
    write_times = 0
    write_failed_times = 0
    rounds_count = 0

    if not CONDITION:
        info: JobInfo = {
            'job_name': job_name,
            'finished_at': None,
            'success': None,
            'error': None,
            'write_times': None,
            'write_failed_times': None,
            'total_fetch_times': None,
            'fallback_records': None,
            'additional_info': {
                '消息': '未满足更新条件',
                '是否为交易日': '是' if CONDITION else '否',
            },
        }
        return info

    code_list = stock_info.get_latest_stock_list()
    n = len(code_list)
    num_batches = math.ceil(n / BATCH_SIZE) if n else 0
    end_date = dt.date.today()

    try:
        for batch_idx in range(num_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, n)
            codes = code_list[start_idx:end_idx]

            df, fallback_records, fetch_times = stock_daily_trade_data_by_tushare.provide(
                codes=codes,
                end_date=end_date,
            )
            total_fallback_records.update(fallback_records)
            total_fetch_times += fetch_times
            rounds_count += 1

            if df is not None and not df.empty:
                flushed = stock_daily_trade_data_buffer.append(df)
                if flushed:
                    write_times += 1
    except ValidError:
        logger.exception('append到buffer过程中校验失败，未写入缓存')
    except BufferWriteError:
        write_times += 1
        write_failed_times += 1
        logger.exception('写入数据库失败')
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
        return JobInfo(
            job_name=job_name,
            finished_at=dt.datetime.now(),
            success=success,
            error=error,
            write_times=write_times,
            write_failed_times=write_failed_times,
            total_fetch_times=total_fetch_times,
            fallback_records=dict(total_fallback_records),
            additional_info={'消息': 'append过程中遇到未预期错误，未写入缓存', '轮次': rounds_count},
        )

    try:
        flushed = stock_daily_trade_data_buffer.flush()
        if flushed:
            write_times += 1
    except BufferWriteError:
        write_times += 1
        write_failed_times += 1
        logger.exception('写入数据库失败')
    except Exception as e:
        logger.exception('未预期错误')
        success = False
        error = e
        return JobInfo(
            job_name=job_name,
            finished_at=dt.datetime.now(),
            success=success,
            error=error,
            write_times=write_times,
            write_failed_times=write_failed_times,
            total_fetch_times=total_fetch_times,
            fallback_records=dict(total_fallback_records),
            additional_info={'消息': 'flush过程中遇到未预期错误，未写入数据库', '轮次': rounds_count},
        )

    return JobInfo(
        job_name=job_name,
        finished_at=dt.datetime.now(),
        success=success,
        error=error,
        write_times=write_times,
        write_failed_times=write_failed_times,
        total_fetch_times=total_fetch_times,
        fallback_records=dict(total_fallback_records),
        additional_info={'消息': '更新股票每日交易数据成功', '轮次': rounds_count},
    )
