import logging
import colorlog
from pathlib import Path
from typing import Optional
# 导入 配置管理文件
from mcp_project.config.settings import settings
class LoggerManager:
    """日志管理器"""
    # _instance 与 __new__: 实现了单例模式。
    # 无论调用多少次 LoggerManager()，返回的永远是内存中的同一个实例。
    _instance: Optional['LoggerManager'] = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._setup_log_directory()

    # 生产环境的鲁棒性体现。
    # 会自动检查并创建 logs/ 文件夹（基于 settings.LOG_FILE ）。如果目录不存在，mkdir(parents=True) 会像 mkdir -p 一样递归创建父目录。
    def _setup_log_directory(self):
        """创建日志目录"""
        log_file = Path(settings.LOG_FILE_PATH)
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # 缓存池。如果在不同的文件里都调用 get_logger("agent")，它会直接从字典返回已配置好的 logger，而不是重新创建。
    _loggers: dict = {}
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志记录器"""
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL))

        # 避免重复添加处理器
        # 关键经验：如果没有这行检查，每当重新获取一次 logger，它就会多挂载一个 handler，导致一条日志被重复打印多次。
        if logger.handlers:
            return logger

        # 控制台处理器（彩色输出）
        # 通过颜色区分 DEBUG (青色) 和 ERROR (红色)，在 PyCharm 的控制台中区分关键信息。
        console_handler = colorlog.StreamHandler()
        # 控制台设为 DEBUG: 方便开发时查看所有细节。
        console_handler.setLevel(logging.DEBUG)
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)

        # 文件处理器
        # logging.FileHandler：生产级设置。
        # 将日志持久化到磁盘 。使用 encoding='utf-8'，这能防止在 Windows 环境下出现中文乱码。
        file_handler = logging.FileHandler(
            # 文件设为 INFO(来源于： settings.LOG_FILE): 避免日志文件因为过多的调试信息而迅速膨胀，只保留核心运行轨迹。
            settings.LOG_FILE_PATH,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        self._loggers[name] = logger
        return logger


# 全局日志管理器实例
logger_manager = LoggerManager()

# 获取日志对象
def get_logger(name: str) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    return logger_manager.get_logger(name)