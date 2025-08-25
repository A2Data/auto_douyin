"""
API模块
提供FastAPI路由和端点
"""

from .app import create_app
from .routes import router

__all__ = [
    "create_app",
    "router",
]