"""
测试服务层
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from video_uploader.models import (
    Config,
    LoginRequest,
    UploadRequest,
    VideoInfo,
    BatchUploadRequest,
)
from video_uploader.services import ConfigService, DouyinService


class TestConfigService:
    """测试配置服务"""
    
    async def test_load_config_from_file(self, temp_dir: Path):
        """测试从文件加载配置"""
        config_file = temp_dir / "config.json"
        
        # 创建测试配置文件
        config_data = {
            "chrome_path": "/test/chrome",
            "cookies_dir": str(temp_dir / "cookies"),
            "logs_dir": str(temp_dir / "logs"),
            "videos_dir": str(temp_dir / "videos")
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        
        service = ConfigService(config_file)
        config = await service.load_config()
        
        assert config.chrome_path == "/test/chrome"
        assert str(config.cookies_dir).endswith("cookies")
    
    async def test_load_config_default(self, temp_dir: Path):
        """测试加载默认配置"""
        config_file = temp_dir / "non_existent.json"
        service = ConfigService(config_file)
        
        config = await service.load_config()
        
        assert config is not None
        assert config.chrome_path is not None
        assert config_file.exists()  # 应该创建默认配置文件
    
    async def test_save_config(self, test_config: Config, temp_dir: Path):
        """测试保存配置"""
        config_file = temp_dir / "config.json"
        service = ConfigService(config_file)
        
        await service.save_config(test_config)
        
        assert config_file.exists()
        
        # 验证保存的内容
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert "chrome_path" in saved_data
        assert "cookies_dir" in saved_data


class TestDouyinService:
    """测试抖音服务"""
    
    @pytest.fixture
    def douyin_service(self, test_config: Config) -> DouyinService:
        """创建抖音服务实例"""
        return DouyinService(test_config)
    
    async def test_login_success(self, douyin_service: DouyinService):
        """测试登录成功"""
        request = LoginRequest(account_name="test_account")
        
        # Mock DouYinUploader
        with patch('video_uploader.services.douyin_service.DouYinUploader') as mock_uploader:
            mock_instance = AsyncMock()
            mock_instance.login.return_value = True
            mock_uploader.return_value = mock_instance
            
            response = await douyin_service.login(request)
            
            assert response.success is True
            assert response.message == "登录成功"
            assert response.account is not None
            assert response.account.name == "test_account"
    
    async def test_login_failure(self, douyin_service: DouyinService):
        """测试登录失败"""
        request = LoginRequest(account_name="test_account")
        
        # Mock DouYinUploader
        with patch('video_uploader.services.douyin_service.DouYinUploader') as mock_uploader:
            mock_instance = AsyncMock()
            mock_instance.login.return_value = False
            mock_uploader.return_value = mock_instance
            
            response = await douyin_service.login(request)
            
            assert response.success is False
            assert response.message == "登录失败"
    
    async def test_upload_video_success(self, douyin_service: DouyinService, temp_dir: Path):
        """测试视频上传成功"""
        # 创建测试视频文件
        video_file = temp_dir / "test_video.mp4"
        video_file.touch()
        
        video_info = VideoInfo(
            video_path=video_file,
            title="测试视频",
            tags=["测试"]
        )
        request = UploadRequest(
            account_name="test_account",
            video_info=video_info
        )
        
        # Mock DouYinUploader
        with patch('video_uploader.services.douyin_service.DouYinUploader') as mock_uploader:
            mock_instance = AsyncMock()
            mock_instance.check_cookie.return_value = True
            mock_instance.upload_video.return_value = True
            mock_uploader.return_value = mock_instance
            
            response = await douyin_service.upload_video(request)
            
            assert response.success is True
            assert response.message == "视频上传成功"
            assert response.title == "测试视频"
    
    async def test_upload_video_cookie_invalid(self, douyin_service: DouyinService, temp_dir: Path):
        """测试Cookie无效的情况"""
        # 创建测试视频文件
        video_file = temp_dir / "test_video.mp4"
        video_file.touch()
        
        video_info = VideoInfo(video_path=video_file)
        request = UploadRequest(
            account_name="test_account",
            video_info=video_info
        )
        
        # Mock DouYinUploader
        with patch('video_uploader.services.douyin_service.DouYinUploader') as mock_uploader:
            mock_instance = AsyncMock()
            mock_instance.check_cookie.return_value = False
            mock_uploader.return_value = mock_instance
            
            response = await douyin_service.upload_video(request)
            
            assert response.success is False
            assert "Cookie无效" in response.message
    
    async def test_batch_upload_success(self, douyin_service: DouyinService, temp_dir: Path):
        """测试批量上传成功"""
        # 创建测试视频文件
        video_files = []
        for i in range(2):
            video_file = temp_dir / f"test_video_{i}.mp4"
            video_file.touch()
            video_files.append(VideoInfo(video_path=video_file, title=f"视频{i}"))
        
        request = BatchUploadRequest(
            account_name="test_account",
            video_list=video_files
        )
        
        # Mock DouYinUploader
        with patch('video_uploader.services.douyin_service.DouYinUploader') as mock_uploader:
            mock_instance = AsyncMock()
            mock_instance.check_cookie.return_value = True
            mock_instance.upload_video.return_value = True
            mock_uploader.return_value = mock_instance
            
            response = await douyin_service.batch_upload(request)
            
            assert response.success is True
            assert response.total_videos == 2
            assert response.success_count == 2
            assert len(response.results) == 2
    
    async def test_check_account_status_no_cookie(self, douyin_service: DouyinService):
        """测试检查账号状态 - 无Cookie文件"""
        account = await douyin_service.check_account_status("test_account")
        
        assert account.name == "test_account"
        assert account.is_logged_in is False
    
    async def test_check_account_status_valid_cookie(self, douyin_service: DouyinService, temp_dir: Path):
        """测试检查账号状态 - 有效Cookie"""
        # 创建Mock的Cookie文件
        cookie_file = douyin_service.config.get_cookie_file_path("test_account")
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        cookie_file.touch()
        
        # Mock DouYinUploader
        with patch('video_uploader.services.douyin_service.DouYinUploader') as mock_uploader:
            mock_instance = AsyncMock()
            mock_instance.check_cookie.return_value = True
            mock_uploader.return_value = mock_instance
            
            account = await douyin_service.check_account_status("test_account")
            
            assert account.name == "test_account"
            assert account.is_logged_in is True