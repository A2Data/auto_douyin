"""
FastAPI应用创建和配置
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from ..services import ConfigService
from ..models import ServerConfig
from ..utils.logger import setup_logging, get_logger
from .routes import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    logger.info("启动抖音MCP服务...")
    
    # 初始化配置服务
    config_service = ConfigService()
    app.state.config_service = config_service
    
    # 加载配置
    config = await config_service.load_config()
    server_config = await config_service.load_server_config()
    
    app.state.config = config
    app.state.server_config = server_config
    
    logger.info("服务初始化完成")
    yield
    logger.info("关闭抖音MCP服务...")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例
    
    Returns:
        FastAPI: 应用实例
    """
    # 设置日志
    setup_logging()
    
    app = FastAPI(
        title="抖音自动上传MCP服务",
        description="基于MCP协议的抖音视频自动上传服务，支持单个和批量上传",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 添加路由
    app.include_router(router, prefix="/api/v1")
    
    # 添加根路由
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """根路径返回简单的HTML页面"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>抖音自动上传MCP服务</title>
            <meta charset="utf-8">
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .container {
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 15px;
                    backdrop-filter: blur(10px);
                }
                h1 { color: #ffffff; text-align: center; }
                .feature {
                    background: rgba(255,255,255,0.1);
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                }
                .api-link {
                    display: inline-block;
                    background: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 5px;
                }
                .api-link:hover {
                    background: #45a049;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎬 抖音自动上传MCP服务</h1>
                <p>基于MCP协议的抖音视频自动上传服务，使用Playwright实现浏览器自动化操作。</p>
                
                <div class="feature">
                    <h3>🔐 账号管理</h3>
                    <p>支持多账号登录和Cookie管理</p>
                </div>
                
                <div class="feature">
                    <h3>📤 视频上传</h3>
                    <p>支持单个视频上传，自动填充标题、标签和缩略图</p>
                </div>
                
                <div class="feature">
                    <h3>⏰ 定时发布</h3>
                    <p>支持指定发布时间的定时发布功能</p>
                </div>
                
                <div class="feature">
                    <h3>🚀 批量上传</h3>
                    <p>支持多视频批量上传和智能时间调度</p>
                </div>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="/docs" class="api-link">📚 API文档</a>
                    <a href="/redoc" class="api-link">📋 ReDoc文档</a>
                </p>
            </div>
        </body>
        </html>
        """
    
    # 健康检查端点
    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "healthy", "service": "douyin-mcp-server"}
    
    return app