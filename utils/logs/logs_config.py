'''
日志配置文件
用于配置日志的输出格式、输出级别、输出位置等
'''

import logging
import os
import time
import datetime

class LogsConfig:
    def __init__(self, log_path):
        self.log_path = log_path
'''