'''
邮件模板
'''
import datetime as dt
import json

from jobs.job_utils import JobInfo


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
    status = '成功' if success else '失败'
    err = _format_error(job_info['error'])
    times = job_info['total_fetch_times']
    fallback = _format_fallback_records(job_info['fallback_records'])
    extra = job_info['additional_info']
    extra_block = _format_additional_info(extra)
    lines = [
        f'任务: {name}',
        f'完成时间: {finished_s}',
        f'状态: {status}',
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
