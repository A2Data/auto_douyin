"""
多平台视频自动上传服务
"""

__version__ = "1.0.0"
__author__ = "Video Uploader Team"
__description__ = "多平台视频自动上传服务"

from .api import create_app

__all__ = ["create_app"]