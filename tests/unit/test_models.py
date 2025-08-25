"""
测试数据模型
"""

import pytest
from datetime import datetime
from pathlib import Path

from video_uploader.models import (
    Config,
    ServerConfig,
    DouyinAccount,
    VideoInfo,
    LoginRequest,
    UploadRequest,
    BatchUploadRequest,
)
from video_uploader.models.douyin import BatchUploadConfig


class TestConfig:
    """测试配置模型"""
    
    def test_config_default_values(self, temp_dir: Path):
        """测试配置默认值"""
        config = Config(
            chrome_path="/test/chrome/path",
            cookies_dir=temp_dir / "cookies",
            logs_dir=temp_dir / "logs", 
            videos_dir=temp_dir / "videos"
        )
        
        assert config.chrome_path == "/test/chrome/path"
        assert config.cookies_dir.exists()
        assert config.logs_dir.exists()
        assert config.videos_dir.exists()
    
    def test_get_cookie_file_path(self, test_config: Config):
        """测试获取Cookie文件路径"""
        account_name = "test_account"
        cookie_path = test_config.get_cookie_file_path(account_name)
        
        assert cookie_path.name == f"douyin_{account_name}.json"
        assert cookie_path.parent == test_config.cookies_dir
    
    def test_get_log_file_path(self, test_config: Config):
        """测试获取日志文件路径"""
        log_name = "test_log"
        log_path = test_config.get_log_file_path(log_name)
        
        assert log_path.name == f"{log_name}.log"
        assert log_path.parent == test_config.logs_dir


class TestServerConfig:
    """测试服务器配置模型"""
    
    def test_server_config_defaults(self):
        """测试服务器配置默认值"""
        config = ServerConfig()
        
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.mcp_server_name == "douyin-uploader"


class TestDouyinAccount:
    """测试抖音账号模型"""
    
    def test_douyin_account_creation(self):
        """测试创建抖音账号"""
        account = DouyinAccount(
            name="test_account",
            is_logged_in=True,
            last_login=datetime.now()
        )
        
        assert account.name == "test_account"
        assert account.is_logged_in is True
        assert account.last_login is not None


class TestVideoInfo:
    """测试视频信息模型"""
    
    def test_video_info_creation(self, temp_dir: Path):
        """测试创建视频信息"""
        # 创建测试视频文件
        video_file = temp_dir / "test_video.mp4"
        video_file.touch()
        
        video_info = VideoInfo(
            video_path=video_file,
            title="测试视频",
            tags=["测试", "视频"],
            location="北京市"
        )
        
        assert video_info.video_path == video_file
        assert video_info.title == "测试视频"
        assert video_info.tags == ["测试", "视频"]
        assert video_info.location == "北京市"
    
    def test_video_info_validation_error(self, temp_dir: Path):
        """测试视频信息验证错误"""
        # 使用不存在的文件
        non_existent_file = temp_dir / "non_existent.mp4"
        
        with pytest.raises(ValueError, match="视频文件不存在"):
            VideoInfo(video_path=non_existent_file)


class TestBatchUploadConfig:
    """测试批量上传配置模型"""
    
    def test_batch_config_defaults(self):
        """测试批量配置默认值"""
        config = BatchUploadConfig()
        
        assert config.videos_per_day == 1
        assert config.daily_times == [9, 12, 15, 18, 21]
        assert config.start_days == 0
    
    def test_batch_config_validation(self):
        """测试批量配置验证"""
        # 测试错误的videos_per_day
        with pytest.raises(ValueError, match="每天发布视频数量必须大于0"):
            BatchUploadConfig(videos_per_day=0)
        
        # 测试错误的daily_times
        with pytest.raises(ValueError, match="时间点必须在0-23之间"):
            BatchUploadConfig(daily_times=[25])
        
        # 测试空的daily_times
        with pytest.raises(ValueError, match="每天发布时间不能为空"):
            BatchUploadConfig(daily_times=[])


class TestRequests:
    """测试请求模型"""
    
    def test_login_request(self):
        """测试登录请求"""
        request = LoginRequest(account_name="test_account")
        assert request.account_name == "test_account"
    
    def test_upload_request(self, temp_dir: Path):
        """测试上传请求"""
        # 创建测试视频文件
        video_file = temp_dir / "test_video.mp4"
        video_file.touch()
        
        video_info = VideoInfo(video_path=video_file)
        request = UploadRequest(
            account_name="test_account",
            video_info=video_info
        )
        
        assert request.account_name == "test_account"
        assert request.video_info.video_path == video_file
        assert request.publish_date is None
    
    def test_batch_upload_request(self, temp_dir: Path):
        """测试批量上传请求"""
        # 创建测试视频文件
        video_files = []
        for i in range(3):
            video_file = temp_dir / f"test_video_{i}.mp4"
            video_file.touch()
            video_files.append(VideoInfo(video_path=video_file))
        
        request = BatchUploadRequest(
            account_name="test_account",
            video_list=video_files
        )
        
        assert request.account_name == "test_account"
        assert len(request.video_list) == 3
        assert isinstance(request.config, BatchUploadConfig)