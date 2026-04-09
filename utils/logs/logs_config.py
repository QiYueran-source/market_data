'''
日志配置常量：输出格式、级别、路径、轮转等。
'''

# 日志保存路径（相对项目根目录）
LOG_DIR = "logs"
FILE_NAME = "app.log"

# 输出与格式
TO_CONSOLE = True # 是否输出到控制台
LOG_LEVEL = "INFO"
LOG_NAME = "app"  # 未传 name 时使用的 logger 名
LOG_FORMAT = "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"

# 轮转配置
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5
