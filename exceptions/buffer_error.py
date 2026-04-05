'''
buffer异常  
'''
from __future__ import annotations

class BufferError(Exception):
    '''缓存异常基类'''

class BufferWriteError(BufferError):
    '''缓存写数据库异常'''

