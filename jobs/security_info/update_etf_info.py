'''
更新时间：每天下午16：20  
限流：300次/min    
'''
# 库
import datetime as dt
from collections import Counter

# 工具
from jobs.job_utils import JobInfo
from db.api.security_info import etf_info
from db.api.trade_calendar import stock_api_trade_calendar

# schema
from schema.security_info import ETF_INFO_SCHEMA

# 提供者
from providers.security_info.eft_info_by_mairui import provide

# 缓存
from storage.buffer import Buffer
etf_info_buffer = Buffer(
    schema = ETF_INFO_SCHEMA,
    buffer_size = 1,
)

# 日志
from utils import get_logger
logger = get_logger('update_etf_info_job')

# 异常
from exceptions.buffer_error import BufferWriteError
from exceptions.valid_error import ValidError

# 条件
UPDATE_INTERVAL = 30 # 天，间隔多久更新一次
UPDATE_ON_CLOSED_DAYS = True # 是否在非交易日更新

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
    total_fallback_records = Counter()
    total_fetch_times = 0
    now_time = dt.datetime.now()
    success = True
    error = None
    write_times = 0
    write_failed_times = 0

    # 条件判断
    days_interval = (dt.date.today() - etf_info.get_latest_update_date()).days
    is_trade_date = stock_api_trade_calendar.is_trade_date(dt.date.today())
    condition = (days_interval > UPDATE_INTERVAL) and (is_trade_date ^ UPDATE_ON_CLOSED_DAYS)

    # 条件满足，更新ETF信息
    if condition:
        try:
            df, fallback_records, fetch_times = provide()
            total_fallback_records.update(fallback_records) # 汇总所有兜底记录  
            total_fetch_times += fetch_times # 汇总总获取次数
            etf_info_buffer.append(df) # 写入缓存
            etf_info_buffer.flush() # 刷新缓存
            write_times += 1
        except ValidError as e:
            logger.exception('append到buffer过程中校验失败，未写入缓存')
            success = False
            error = e
        except BufferWriteError as e:
            write_times += 1
            write_failed_times += 1
            logger.exception('写入数据库失败')
            success = False
            error = e
        except Exception as e:
            logger.exception('未预期错误')
            success = False
            error = e
        finally:
            info:JobInfo = {
                'job_name': 'update_etf_info',
                'finished_at': now_time,
                'success': success,
                'error': error,
                'write_times': write_times,
                'write_failed_times': write_failed_times,
                'total_fetch_times': total_fetch_times,
                'fallback_records': dict(total_fallback_records),
                'additional_info': {}
            }
            return info
    # 条件不满足，仅返回JobInfo信息
    else:
        info:JobInfo = {
            'job_name': 'update_etf_info',
            'finished_at': None,
            'success': None,
            'error': None,
            'write_times': None,
            'write_failed_times': None,
            'total_fetch_times': None,
            'fallback_records': None,
            'additional_info': {
                '消息':'未满足更新条件',
                '距离下次更新还剩': f'{max(0, UPDATE_INTERVAL - days_interval)} 天', 
                '是否为交易日': '是' if is_trade_date else '否'}
            }
        return info