"""
配置服务
负责配置的加载、保存和管理
"""

import json
from pathlib import Path
from typing import Optional

from ..models import Config, ServerConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ConfigService:
    """配置服务类"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        初始化配置服务
        
        Args:
            config_file: 配置文件路径，默认为 data/config.json
        """
        self.config_file = config_file or Path("data/config.json")
        self._config: Optional[Config] = None
        self._server_config: Optional[ServerConfig] = None
    
    async def load_config(self) -> Config:
        """
        加载应用配置
        
        Returns:
            Config: 配置对象
        """
        if self._config is not None:
            return self._config
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._config = Config(**config_data)
                logger.info(f"已加载配置文件: {self.config_file}")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
                self._config = Config()
        else:
            logger.info("配置文件不存在，使用默认配置")
            self._config = Config()
            await self.save_config(self._config)
        
        return self._config
    
    async def load_server_config(self) -> ServerConfig:
        """
        加载服务器配置
        
        Returns:
            ServerConfig: 服务器配置对象
        """
        if self._server_config is not None:
            return self._server_config
        
        # 可以从环境变量或配置文件加载
        self._server_config = ServerConfig()
        return self._server_config
    
    async def save_config(self, config: Config) -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置对象
        """
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            config_dict = config.model_dump(mode='json')
            # 将Path对象转换为字符串
            for key, value in config_dict.items():
                if isinstance(value, Path):
                    config_dict[key] = str(value)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self._config = config
            logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    def get_config(self) -> Optional[Config]:
        """获取当前配置（同步方法）"""
        return self._config
    
    def get_server_config(self) -> Optional[ServerConfig]:
        """获取当前服务器配置（同步方法）"""
        return self._server_config