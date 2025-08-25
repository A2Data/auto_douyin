# -*- coding: utf-8 -*-

"""
日志管理模块
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from loguru import logger


class Logger:
    """日志管理类"""

    def __init__(self, name: str, log_file: Optional[str] = None, level: str = "INFO"):
        """
        初始化日志器

        Args:
            name: 日志器名称
            log_file: 日志文件路径
            level: 日志级别
        """
        self.name = name
        self.log_file = log_file
        self.level = level
        self._setup_logger()

    def _setup_logger(self):
        """设置日志器"""
        # 配置日志格式
        self.log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        # 如果指定了日志文件，添加文件处理器
        if self.log_file:
            # 确保日志目录存在
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # 添加文件日志处理器
            logger.add(
                self.log_file,
                format=self.log_format,
                level=self.level,
                rotation="10 MB",
                retention="10 days",
                compression="zip",
                encoding="utf-8"
            )

    def get_logger(self):
        """获取日志器"""
        return logger.bind(name=self.name)


# 全局日志配置
_loggers = {}


def setup_logging(log_level: str = "INFO"):
    """
    设置全局日志配置

    Args:
        log_level: 日志级别
    """
    # 移除默认的日志处理器
    logger.remove()

    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> - "
            "<level>{message}</level>"
        ),
        level=log_level,
        colorize=True
    )


def get_logger(name: str, log_file: Optional[str] = None, level: str = "INFO"):
    """
    获取日志器

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        日志器实例
    """
    if name not in _loggers:
        _loggers[name] = Logger(name, log_file, level)

    return _loggers[name].get_logger()


def get_douyin_logger(log_file: Optional[str] = None):
    """
    获取抖音专用日志器

    Args:
        log_file: 日志文件路径

    Returns:
        抖音日志器
    """
    if not log_file:
        log_file = str(Path(__file__).parent / "logs" / "douyin.log")

    return get_logger("douyin", log_file)


def get_service_logger(log_file: Optional[str] = None):
    """
    获取服务专用日志器

    Args:
        log_file: 日志文件路径

    Returns:
        服务日志器
    """
    if not log_file:
        log_file = str(Path(__file__).parent / "logs" / "service.log")

    return get_logger("service", log_file)


# 预定义的日志器
def create_default_loggers():
    """创建默认日志器"""
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # 创建各种日志器
    loggers = {
        "douyin": get_douyin_logger(),
        "service": get_service_logger(),
        "main": get_logger("main", str(logs_dir / "main.log")),
        "error": get_logger("error", str(logs_dir / "error.log"), "ERROR")
    }

    return loggers


# 辅助函数
def log_function_call(func_name: str, args: tuple = (), kwargs: dict = None):
    """
    记录函数调用

    Args:
        func_name: 函数名称
        args: 位置参数
        kwargs: 关键字参数
    """
    main_logger = get_logger("main")
    kwargs = kwargs or {}
    main_logger.debug(f"调用函数: {func_name}, 参数: args={args}, kwargs={kwargs}")


def log_error(error: Exception, context: str = ""):
    """
    记录错误信息

    Args:
        error: 异常对象
        context: 错误上下文
    """
    error_logger = get_logger("error")
    error_logger.error(f"错误: {str(error)}, 上下文: {context}", exc_info=True)


if __name__ == "__main__":
    # 测试日志功能
    setup_logging("DEBUG")

    # 测试各种日志器
    douyin_logger = get_douyin_logger()
    service_logger = get_service_logger()
    main_logger = get_logger("main")

    douyin_logger.info("这是抖音日志测试")
    service_logger.info("这是服务日志测试")
    main_logger.info("这是主日志测试")

    # 测试错误记录
    try:
        raise ValueError("测试错误")
    except ValueError as e:
        log_error(e, "测试错误记录")

    print("日志测试完成")