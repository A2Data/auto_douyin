#!/usr/bin/env python3
"""
多平台视频上传服务
支持抖音、微信视频号、小红书、Bilibili、快手等平台
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .api.app import create_app
from .utils.logger import logger


async def main() -> None:
    """主函数"""
    try:
        # 创建FastAPI应用
        app = create_app()
        logger.info("视频上传服务启动完成")
        
        # 这里可以添加其他初始化逻辑
        
    except Exception as e:
        logger.error(f"启动视频上传服务时发生错误: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())