"""
模型定义模块
定义所有数据结构的强类型
"""

from .config import Config, ServerConfig
from .douyin import (
    DouyinAccount,
    VideoInfo,
    UploadRequest,
    UploadResponse,
    BatchUploadRequest,
    BatchUploadResponse,
    LoginRequest,
    LoginResponse,
)

__all__ = [
    "Config",
    "ServerConfig", 
    "DouyinAccount",
    "VideoInfo",
    "UploadRequest",
    "UploadResponse",
    "BatchUploadRequest",
    "BatchUploadResponse",
    "LoginRequest",
    "LoginResponse",
]