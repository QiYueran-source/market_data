'''
任务执行信息类：  

run函数返回执行信息给main函数，用于邮件通知
'''
import datetime as dt
from typing import TypedDict, List, Dict

class JobInfo(TypedDict):
    '''
    任务执行信息类  
    
    - job_name: str 任务名称
    - finished_at: dt.datetime 执行完成时间
    - success: bool 是否成功
    - error: Exception | None 错误信息
    - total_fetch_times: int 总获取次数  
    - fallback_records: Dict[str, int] 兜底记录，key:兜底原因，value:兜底次数
    - additional_info: dict | None 额外信息
    '''
    # 基础信息
    job_name: str
    finished_at: dt.datetime

    # 执行结果
    success: bool # 是否成功
    error: Exception | None # 错误信息

    # 执行详情
    total_fetch_times: int # 总获取次数  
    fallback_records: Dict[str, int] # 兜底记录，key:兜底原因，value:兜底次数

    # 额外信息
    additional_info: dict | None # 额外信息
    