# -*- coding: utf-8 -*-

"""
配置管理模块
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """配置类"""

    def __init__(self, config_data: Dict[str, Any] = None):
        """
        初始化配置

        Args:
            config_data: 配置数据字典
        """
        self.config_data = config_data or {}
        self.base_dir = Path(__file__).parent

        # 从配置数据获取各项设置
        self.chrome_path = self.config_data.get('chrome_path', '')
        self.cookies_dir = self.config_data.get('cookies_dir', str(self.base_dir / 'cookies'))
        self.logs_dir = self.config_data.get('logs_dir', str(self.base_dir / 'logs'))
        self.videos_dir = self.config_data.get('videos_dir', str(self.base_dir / 'videos'))

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        for directory in [self.cookies_dir, self.logs_dir, self.videos_dir]:
            os.makedirs(directory, exist_ok=True)

    def get_cookie_file_path(self, account_name: str) -> str:
        """
        获取Cookie文件路径

        Args:
            account_name: 账号名称

        Returns:
            Cookie文件路径
        """
        return str(Path(self.cookies_dir) / f"douyin_{account_name}.json")

    def get_log_file_path(self, log_name: str) -> str:
        """
        获取日志文件路径

        Args:
            log_name: 日志名称

        Returns:
            日志文件路径
        """
        return str(Path(self.logs_dir) / f"{log_name}.log")

    def get_video_file_path(self, filename: str) -> str:
        """
        获取视频文件路径

        Args:
            filename: 文件名

        Returns:
            视频文件路径
        """
        return str(Path(self.videos_dir) / filename)

    def update_config(self, key: str, value: Any):
        """
        更新配置

        Args:
            key: 配置键
            value: 配置值
        """
        self.config_data[key] = value
        setattr(self, key, value)

    def save_config(self, config_file: str):
        """
        保存配置到文件

        Args:
            config_file: 配置文件路径
        """
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, config_file: str) -> 'Config':
        """
        从文件加载配置

        Args:
            config_file: 配置文件路径

        Returns:
            Config实例
        """
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        else:
            config_data = {}

        return cls(config_data)


def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置

    Returns:
        默认配置字典
    """
    # 根据操作系统设置默认Chrome路径
    import platform
    system = platform.system()

    if system == "Windows":
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    elif system == "Darwin":  # macOS
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:  # Linux
        chrome_path = "/usr/bin/google-chrome"

    return {
        "chrome_path": chrome_path,
        "cookies_dir": "./cookies",
        "logs_dir": "./logs",
        "videos_dir": "./videos"
    }


def setup_config(config_file: Optional[str] = None) -> Config:
    """
    设置配置

    Args:
        config_file: 配置文件路径，如果为None则使用默认配置

    Returns:
        Config实例
    """
    if config_file and os.path.exists(config_file):
        return Config.load_from_file(config_file)
    else:
        # 使用默认配置
        base_dir = Path(__file__).parent
        default_config_file = base_dir / "config.json"

        if not default_config_file.exists():
            # 创建默认配置文件
            default_config = get_default_config()
            with open(default_config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return Config(default_config)
        else:
            return Config.load_from_file(str(default_config_file))


def create_sample_config():
    """创建示例配置文件"""
    config = get_default_config()
    config_file = Path(__file__).parent / "config.json"

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"示例配置文件已创建: {config_file}")


if __name__ == "__main__":
    # 创建示例配置文件
    create_sample_config()