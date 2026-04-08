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
    - success: Optional[bool] 是否成功：run 未因「未预期异常」中断时为 True；Provider 兜底、Buffer 校验/写库等可预期失败由计数字段体现，不一定置 False（见各 job 约定）
    - error: Optional[Exception] 仅「未预期」异常实例。预期路径上的 ValidError、BufferWriteError、已在 Provider 内消化的 ApiError 等 **不** 写入本字段，而用 write_failed_times、fallback_records 等统计，详情见 logger.exception
    - write_times: Optional[int] 成功 flush/计入写入的次数（循环写库时累计）
    - write_failed_times: Optional[int] 校验失败或写库失败等 **可预期** 失败次数（与 error 互斥补充，不重复塞入 error）
    - total_fetch_times: Optional[int] 总拉取次数
    - fallback_records: Optional[Dict[str, int]] Provider 侧兜底：key 为原因标识，value 为次数
    - additional_info: Optional[dict] 额外信息（如跳过原因、非致命说明）
    '''
    # 基础信息
    job_name: Optional[str]
    finished_at: Optional[dt.datetime]

    # 执行结果
    success: Optional[bool]
    error: Optional[Exception]

    # 插入数据库结果
    write_times: Optional[int]
    write_failed_times: Optional[int]

    # 执行详情
    total_fetch_times: Optional[int]
    fallback_records: Optional[Dict[str, int]]

    # 额外信息
    additional_info: Optional[dict]
    