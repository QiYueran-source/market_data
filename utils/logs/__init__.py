import logging
import logging.handlers
import os

from utils.logs.logs_config import (
    BACKUP_COUNT,
    FILE_NAME,
    LOG_DIR,
    LOG_FORMAT,
    LOG_LEVEL,
    LOG_NAME,
    MAX_BYTES,
    TO_CONSOLE,
)

__all__ = ["get_logger"]

_configured = False


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _setup_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    log_dir = os.path.join(_project_root(), LOG_DIR)
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, FILE_NAME)

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if TO_CONSOLE:
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(formatter)
        root.addHandler(console)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    返回 logger，首次调用时初始化根日志（单文件 + 可选控制台、轮转）。
    name 建议使用 __name__；省略时使用 LOG_NAME。
    """
    _setup_logging()
    return logging.getLogger(name if name is not None else LOG_NAME)
