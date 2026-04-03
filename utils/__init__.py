'''
工具模块  
1.日志相关工具: get_logger()
2.路径相关工具: add_root_path(), 需要在入口脚本开头调用
'''

from .logs.logs_config import get_logger
from .set_path import add_root_path

__all__ = ['get_logger', 'add_root_path']