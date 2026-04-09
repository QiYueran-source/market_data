'''
邮件模板  
- gen_job_statics_body: 生成job开头统计信息  
- jobinfo_to_email_body: 将 job_info 转换为单段邮件正文（纯文本）。  
'''
import datetime as dt
import json

from models.job_info import JobInfo


def _format_dt(value: dt.datetime) -> str:
    return value.strftime('%Y-%m-%d %H:%M:%S')


def _format_error(err: Exception | None) -> str:
    if err is None:
        return ''
    return str(err)


def _format_fallback_records(records: dict[str, int]) -> str:
    if not records:
        return '无'
    lines = [f'  {reason}: {count}' for reason, count in sorted(records.items())]
    return '\n'.join(lines)


def _format_additional_info(info: dict | None) -> str:
    if not info:
        return ''
    try:
        return json.dumps(info, ensure_ascii=False, indent=2)
    except TypeError:
        return repr(info)


def jobinfo_to_email_body(job_info: JobInfo) -> str:
    '''
    将 job_info 转换为单段邮件正文（纯文本）。

    - 参数
        - job_info: JobInfo 任务执行信息

    - 返回
        - str: 邮件内容片段
    '''
    name = job_info['job_name']
    finished = job_info['finished_at']
    finished_s = _format_dt(finished) if isinstance(finished, dt.datetime) else str(finished)
    success = job_info['success']
    err = _format_error(job_info['error'])
    write_times = job_info['write_times']
    write_failed_times = job_info['write_failed_times']
    times = job_info['total_fetch_times']
    fallback = _format_fallback_records(job_info['fallback_records'])
    extra = job_info['additional_info']
    extra_block = _format_additional_info(extra)
    lines = [
        f'任务: {name}',
        f'完成时间: {finished_s}',
        f'写入数据库次数: {write_times}',
        f'写入数据库失败次数: {write_failed_times}',
        f'总获取次数: {times}',
        '兜底记录:',
        fallback,
    ]
    if not success and err:
        lines.append(f'错误: {err}')
    if extra_block:
        lines.append('额外信息:')
        lines.append(extra_block)
    return '-' * 60 + '\n' + '\n'.join(lines) + '\n' 


def gen_job_statics_body(total_jobs:int, success_jobs:int)->str:
    '''生成job开头统计信息'''
    return f'执行jobs数量：{total_jobs} 个jobs' + '\n' + f'执行成功数量：{success_jobs}' + '\n' + '具体执行结果如下：' + '\n'