"""
配置模型定义
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import platform


class Config(BaseModel):
    """应用配置模型"""
    
    chrome_path: str = Field(description="Chrome浏览器路径")
    cookies_dir: Path = Field(default=Path("./cookies"), description="Cookie存储目录")
    logs_dir: Path = Field(default=Path("./logs"), description="日志存储目录")
    videos_dir: Path = Field(default=Path("./videos"), description="视频文件目录")
    
    @field_validator("chrome_path", mode="before")
    @classmethod
    def set_default_chrome_path(cls, v: Optional[str]) -> str:
        if v:
            return v
        
        system = platform.system()
        if system == "Windows":
            return "C:/Program Files/Google/Chrome/Application/chrome.exe"
        elif system == "Darwin":  # macOS
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        else:  # Linux
            return "/usr/bin/google-chrome"
    
    @field_validator("cookies_dir", "logs_dir", "videos_dir", mode="after")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    def get_cookie_file_path(self, account_name: str) -> Path:
        """获取指定账号的Cookie文件路径"""
        return self.cookies_dir / f"douyin_{account_name}.json"
    
    def get_log_file_path(self, log_name: str) -> Path:
        """获取指定日志文件路径"""
        return self.logs_dir / f"{log_name}.log"


class ServerConfig(BaseModel):
    """服务器配置模型"""
    
    host: str = Field(default="0.0.0.0", description="服务器监听地址")
    port: int = Field(default=8000, description="服务器端口")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    
    # MCP相关配置
    mcp_server_name: str = Field(default="douyin-uploader", description="MCP服务器名称")
    mcp_server_version: str = Field(default="1.0.0", description="MCP服务器版本")