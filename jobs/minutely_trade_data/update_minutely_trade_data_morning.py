'''
分钟交易数据: 上午 9:30-11:30

所有的分钟交易统一走该脚本
'''
# 库
import datetime as dt
from collections import Counter
import time

# 工具
from models.job_info import JobInfo

# ETF配置
from jobs.minutely_trade_data.shared_config import ETF_CODE_LIST, ETF_BUFFER_MAP, etf_minutely_trade_data_by_mairui

# 早盘收盘
from jobs.minutely_trade_data.shared_config import MORNING_MARKET_END_TIME

# 共享配置
from jobs.minutely_trade_data.shared_config import (
    INTERVAL_SECONDS,
    CONDITION
)

# 日志
from utils import get_logger
logger = get_logger('minutely_trade_data_etf_job_morning')

# 异常
from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError


def run()->JobInfo:
    '''
    执行入口  
    
    逻辑：
    获取最新更新日期，如果：  
        - 距离上次更新超过 UPDATE_INTERVAL 天  
        - 处于非交易日  
    则更新

    否则，不更新，提供jobinfo信息
    
    返回：
    - JobInfo: 执行信息，用于邮件通知  
    '''
    job_name = 'update_minutely_trade_data_morning'
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
    
    # 条件满足，更新分钟交易数据
    while dt.datetime.now().time() < MORNING_MARKET_END_TIME:
        now_time = dt.datetime.now()
        # provide数据
        try:
            # etf
            etf_dfs, etf_fallback_records, etf_fetch_times = etf_minutely_trade_data_by_mairui.provide(ETF_CODE_LIST)
            total_fallback_records.update(etf_fallback_records)
            total_fetch_times += etf_fetch_times
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
                additional_info={'消息': 'provide过程中遇到未预期错误，未写入缓存'}
            )
            return info
    
        # etf写入缓存
        for code, df in etf_dfs.items():
            try:
                flushed = ETF_BUFFER_MAP[code].append(df)
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
        rounds_count += 1
        elapsed = (dt.datetime.now() - now_time).total_seconds()
        if elapsed < INTERVAL_SECONDS:
            logger.debug(f'等待{INTERVAL_SECONDS - elapsed}秒后继续')
            time.sleep(INTERVAL_SECONDS - elapsed)
        

    # 最后flush缓存
    # etf
    for code in ETF_BUFFER_MAP.keys():
        try:
            flushed = ETF_BUFFER_MAP[code].flush()
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
            
    info = JobInfo(
        job_name=job_name,
        finished_at=dt.datetime.now(),
        success=success,
        error=error,
        write_times=write_times,
        write_failed_times=write_failed_times,
        total_fetch_times=total_fetch_times,
        fallback_records=dict(total_fallback_records),
        additional_info={
            '消息': '更新分钟交易数据成功',
            '轮次': rounds_count
        }
    )
    return info