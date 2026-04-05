'''
API 限流工具

滑动窗口 Sliding Window：任意连续 window_sec 秒内最多允许 max_requests 次 acquire。
用于在 Provider 原子请求前调用，使「一次请求」对应「一次限流」。

全局限流器：  
每一个数据源适配一个全局限流器，用于限制该数据源的请求次数。
- akshare  
- mairui  
- tushare  
- stock_api  

限流装饰器：  
limit(source:Literal['akshare', 'mairui', 'tushare', 'stock_api'])  
装饰provide方法，使其在调用时进行限流。  

日志：
本工具的日志级别为DEBUG，用于记录限流器的等待时间。
'''
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Literal, Callable, Any
from functools import wraps

# 日志
from utils import get_logger
logger = get_logger('api_limiter')


class SlidingWindowLimiter:
    '''
    线程安全的滑动窗口限流器。

    参数:
    - window_sec: 窗口长度（秒），须 > 0
    - max_requests: 窗口内最多允许的请求次数，须 >= 1
    - light_offset: 轻微偏移，避免卡在线的临界点
    '''

    def __init__(
        self, 
        window_sec: float, 
        max_requests: int,
        light_offset: float = 0.1
    ) -> None:
        self._window_sec = float(window_sec)
        self._max_requests = int(max_requests)
        self._times: deque[float] = deque()
        self._light_offset = float(light_offset)
        self._lock = threading.Lock()

    @property
    def window_sec(self) -> float:
        return self._window_sec

    @property
    def max_requests(self) -> int:
        return self._max_requests

    def acquire(self) -> None:
        '''
        阻塞直到窗口内可容纳 1 次请求，并登记一个时间戳。

        每次原子化 HTTP/SDK 调用前调用一次即可；一次 acquire 固定对应一次配额。
        '''
        while True:
            with self._lock:
                now = time.monotonic()
                while self._times and self._times[0] <= now - self._window_sec:
                    self._times.popleft()

                if len(self._times) < self._max_requests:
                    self._times.append(now)
                    return

                wait = self._times[0] + self._window_sec - now

            if wait > 0:
                logger.debug(f'开始等待，时间: {wait}')
                time.sleep(wait + self._light_offset)

    def __repr__(self) -> str:
        return (
            f'SlidingWindowLimiter(window_sec={self._window_sec!r}, '
            f'max_requests={self._max_requests!r})'
        )

# 全局限流器
TEST_LIMITER = SlidingWindowLimiter(window_sec=30, max_requests=60)
TUSHARE_LIMITER = SlidingWindowLimiter(window_sec=1, max_requests=100)
MAIRUI_LIMITER = SlidingWindowLimiter(window_sec=1, max_requests=100)
AKSHARE_LIMITER = SlidingWindowLimiter(window_sec=1, max_requests=100)
STOCK_API_TRADE_CALENDAR_LIMITER = SlidingWindowLimiter(window_sec=60, max_requests=40)

SOURCE_LIMITERS_MAP = {
    'akshare': AKSHARE_LIMITER,
    'mairui': MAIRUI_LIMITER,
    'tushare': TUSHARE_LIMITER,
    'stock_api_trade_calendar': STOCK_API_TRADE_CALENDAR_LIMITER,
    'test': TEST_LIMITER,
}

# 限流装饰器
def limit(source:Literal['akshare', 'mairui', 'tushare', 'stock_api_trade_calendar', 'test']) -> Callable:
    def decorater(func:Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            SOURCE_LIMITERS_MAP[source].acquire()
            return func(*args, **kwargs)
        return wrapper
    return decorater