'''
重试工具

提供重试装饰器，用于装饰需要重试的函数。
需要提供捕获的异常类型，以及尝试总次数与间隔。

日志：
本工具的日志级别为DEBUG，用于记录重试的次数和间隔。
'''
from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Tuple, Type

# 日志
from utils import get_logger
logger = get_logger('retry')

def retry(
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    retry_delay: float = 1.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    '''
    重试装饰器

    若被装饰函数抛出 retry_exceptions 中的任一类型，则在等待 retry_delay 秒后再次调用，
    直到成功返回，或达到 max_attempts 次尝试；最后一次仍失败则原样抛出该异常。

    参数:
    - retry_exceptions: 需要触发重试的异常类型元组，默认 (Exception,)
    - max_attempts: 总共尝试次数（含第一次），至少为 1，默认 3
    - retry_delay: 相邻两次尝试之间的间隔（秒），默认 1.0；最后一次失败后不再 sleep
    '''
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions:
                    logger.debug(f'重试次数: {attempt}')
                    if attempt == max_attempts - 1:
                        logger.debug(f'达到最大重试次数：{max_attempts}，抛出异常')
                        raise
                    time.sleep(retry_delay)

        return wrapper

    return decorator
