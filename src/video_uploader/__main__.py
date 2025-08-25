#!/usr/bin/env python3
"""
主入口文件 - 支持 python -m video_uploader 运行
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())