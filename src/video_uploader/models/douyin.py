"""
抖音相关数据模型定义
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DouyinAccount(BaseModel):
    """抖音账号模型"""
    
    name: str = Field(description="账号名称")
    cookie_file: Optional[Path] = Field(default=None, description="Cookie文件路径")
    is_logged_in: bool = Field(default=False, description="是否已登录")
    last_login: Optional[datetime] = Field(default=None, description="最后登录时间")


class VideoInfo(BaseModel):
    """视频信息模型"""
    
    video_path: Path = Field(description="视频文件路径")
    title: Optional[str] = Field(default=None, description="视频标题")
    tags: List[str] = Field(default_factory=list, description="话题标签列表")
    thumbnail_path: Optional[Path] = Field(default=None, description="缩略图路径")
    location: str = Field(default="北京市", description="地理位置")
    
    @field_validator("video_path", mode="after")
    @classmethod
    def validate_video_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"视频文件不存在: {v}")
        return v
    
    @field_validator("thumbnail_path", mode="after")
    @classmethod
    def validate_thumbnail_exists(cls, v: Optional[Path]) -> Optional[Path]:
        if v and not v.exists():
            raise ValueError(f"缩略图文件不存在: {v}")
        return v


class LoginRequest(BaseModel):
    """登录请求模型"""
    
    account_name: str = Field(description="账号名称")


class LoginResponse(BaseModel):
    """登录响应模型"""
    
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    cookie_file: Optional[str] = Field(default=None, description="Cookie文件路径")
    account: Optional[DouyinAccount] = Field(default=None, description="账号信息")


class UploadRequest(BaseModel):
    """上传请求模型"""
    
    account_name: str = Field(description="账号名称")
    video_info: VideoInfo = Field(description="视频信息")
    publish_date: Optional[datetime] = Field(default=None, description="发布时间(None表示立即发布)")


class UploadResponse(BaseModel):
    """上传响应模型"""
    
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    title: Optional[str] = Field(default=None, description="视频标题")
    upload_time: datetime = Field(default_factory=datetime.now, description="上传时间")


class BatchUploadConfig(BaseModel):
    """批量上传配置模型"""
    
    videos_per_day: int = Field(default=1, description="每天上传视频数量")
    daily_times: List[int] = Field(default=[9, 12, 15, 18, 21], description="每天上传的时间点")
    start_days: int = Field(default=0, description="从几天后开始上传")
    
    @field_validator("videos_per_day")
    @classmethod
    def validate_videos_per_day(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("每天发布视频数量必须大于0")
        return v
    
    @field_validator("daily_times")
    @classmethod
    def validate_daily_times(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("每天发布时间不能为空")
        for hour in v:
            if not (0 <= hour <= 23):
                raise ValueError(f"时间点必须在0-23之间: {hour}")
        return sorted(v)


class BatchUploadRequest(BaseModel):
    """批量上传请求模型"""
    
    account_name: str = Field(description="账号名称")
    video_list: List[VideoInfo] = Field(description="视频列表")
    config: BatchUploadConfig = Field(default_factory=BatchUploadConfig, description="批量上传配置")


class BatchUploadResponse(BaseModel):
    """批量上传响应模型"""
    
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    total_videos: int = Field(description="总视频数量")
    success_count: int = Field(description="成功上传数量")
    results: List[UploadResponse] = Field(description="详细结果列表")