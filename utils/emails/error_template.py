'''
编排层邮件正文/主题模板：根据 job 名称 → 异常的映射生成纯文本。

不依赖 send_email，仅返回 str，供调用方传入 send_email。
'''
from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Mapping

__all__ = [
    'job_run_email_subject',
    'job_run_email_body',
]


def job_run_email_subject(
    name: str,
    errors: Mapping[str, BaseException],
    *,
    success_suffix: str = '成功',
    failure_suffix: str = '失败',
) -> str:
    '''
    生成批量任务汇总邮件的主题（一行）。

    :param name: 任务域名称，如「交易日历更新统计」
    :param errors: job_name -> 异常；空表示全部成功
    '''
    if not errors:
        return f'{name} — {success_suffix}'
    n = len(errors)
    return f'{name} — {failure_suffix}（{n}）'


def job_run_email_body(
    title: str,
    errors: Mapping[str, BaseException],
    *,
    success_message: str = '所有任务均已成功执行。',
    failure_intro: str = '以下任务执行失败：',
    include_traceback: bool = False,
    max_traceback_chars: int = 4000,
    timestamp_utc: datetime | None = None,
) -> str:
    '''
    生成批量任务汇总邮件正文（UTF-8 纯文本）。

    :param title: 正文顶部标题（可与 subject 中的 name 相同）
    :param errors: job_name -> 异常；空则只输出成功说明与时间
    :param include_traceback: 是否为每条异常附加 traceback（可能较长）
    :param max_traceback_chars: 单条 traceback 最大字符数，超出截断
    :param timestamp_utc: 报告时间；默认当前 UTC
    '''
    ts = timestamp_utc or datetime.now(timezone.utc)
    sep = '=' * min(len(title), 72)
    lines: list[str] = [
        title,
        sep,
        f'时间（UTC）: {ts.isoformat(timespec="seconds")}',
        '',
    ]

    if not errors:
        lines.append(success_message)
        return '\n'.join(lines)

    lines.append(failure_intro)
    lines.append('')

    for job_name, exc in errors.items():
        lines.append(f'--- {job_name} ---')
        lines.append(f'类型: {type(exc).__name__}')
        lines.append(f'信息: {exc}')
        if include_traceback and exc.__traceback__ is not None:
            tb = ''.join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
            if len(tb) > max_traceback_chars:
                tb = tb[:max_traceback_chars] + '\n... [traceback 已截断]'
            lines.append('堆栈:')
            lines.append(tb)
        lines.append('')

    return '\n'.join(lines).rstrip() + '\n'
