"""
测试配置和fixtures
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient

from video_uploader import create_app
from video_uploader.models import Config
from video_uploader.services import ConfigService


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
async def test_config(temp_dir: Path) -> Config:
    """创建测试配置"""
    return Config(
        chrome_path="/fake/chrome/path",
        cookies_dir=temp_dir / "cookies",
        logs_dir=temp_dir / "logs",
        videos_dir=temp_dir / "videos"
    )


@pytest.fixture
async def config_service(test_config: Config, temp_dir: Path) -> ConfigService:
    """创建配置服务"""
    config_file = temp_dir / "config.json"
    service = ConfigService(config_file)
    await service.save_config(test_config)
    return service


@pytest.fixture
def test_client() -> TestClient:
    """创建测试客户端"""
    app = create_app()
    return TestClient(app)