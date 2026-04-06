'''
任务执行信息类：  

run函数返回执行信息给main函数，用于邮件通知
'''
import datetime as dt
from typing import TypedDict, Dict, Optional

class JobInfo(TypedDict):
    '''
    任务执行信息类  
    
    - job_name: Optional[str] 任务名称
    - finished_at: Optional[dt.datetime] 执行完成时间
    - success: Optional[bool] 是否成功
    - error: Optional[Exception] 错误信息
    - write_times: Optional[int] 写入数据库次数 （循环写库，这个字段用于统计总次数）
    - write_failed_times: Optional[int] 写入数据库失败次数 （循环写库，这个字段用于统计失败次数）
    - total_fetch_times: Optional[int] 总获取次数  
    - fallback_records: Optional[Dict[str, int]] 兜底记录，key:兜底原因，value:兜底次数
    - additional_info: Optional[dict] 额外信息
    '''
    # 基础信息
    job_name: Optional[str]
    finished_at: Optional[dt.datetime]

    # 执行结果
    success: Optional[bool] # 是否成功 (只要完整跑完就算成功，兜底也算成功)
    error: Optional[Exception] # 错误信息

    # 插入数据库结果
    write_times: Optional[int] # 写入数据库次数 （后续循环写库，这个字段用于统计总次数）
    write_failed_times: Optional[int] # 写入数据库失败次数 （后续循环写库，这个字段用于统计失败次数）

    # 执行详情
    total_fetch_times: Optional[int] # 总获取次数  
    fallback_records: Optional[Dict[str, int]] # 兜底记录，key:兜底原因，value:兜底次数

    # 额外信息
    additional_info: Optional[dict] # 额外信息
    