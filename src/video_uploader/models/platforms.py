"""
多平台通用数据模型定义
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class BaseAccount(BaseModel):
    """账号基类"""
    
    name: str = Field(description="账号名称")
    platform: str = Field(description="平台名称")
    cookie_file: Optional[Path] = Field(default=None, description="Cookie文件路径")
    is_logged_in: bool = Field(default=False, description="是否已登录")
    last_login: Optional[datetime] = Field(default=None, description="最后登录时间")


class BaseVideoInfo(BaseModel):
    """视频信息基类"""
    
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


# 抖音平台模型
class DouyinAccount(BaseAccount):
    """抖音账号模型"""
    platform: str = "douyin"


class DouyinVideoInfo(BaseVideoInfo):
    """抖音视频信息"""
    privacy: Literal["public", "private", "friends"] = Field(default="public", description="隐私设置")
    allow_comment: bool = Field(default=True, description="允许评论")
    allow_duet: bool = Field(default=True, description="允许合拍")
    allow_stitch: bool = Field(default=True, description="允许拼接")


# 微信视频号平台模型
class WechatChannelAccount(BaseAccount):
    """微信视频号账号模型"""
    platform: str = "wechat_channel"


class WechatChannelVideoInfo(BaseVideoInfo):
    """微信视频号内容信息（支持视频和图文）"""
    description: Optional[str] = Field(default=None, description="内容描述")
    original_statement: bool = Field(default=True, description="声明原创")
    location_visible: bool = Field(default=True, description="显示位置")
    sync_to_moments: bool = Field(default=False, description="同步到朋友圈")
    content_type: Literal["video", "image"] = Field(default="video", description="内容类型：video（视频）或 image（图文）")
    image_paths: List[str] = Field(default_factory=list, description="图文内容的图片路径列表")


# 小红书平台模型
class XiaohongshuAccount(BaseAccount):
    """小红书账号模型"""
    platform: str = "xiaohongshu"


class XiaohongshuVideoInfo(BaseVideoInfo):
    """小红书视频信息"""
    description: str = Field(description="视频描述")
    topic_tags: List[str] = Field(default_factory=list, description="话题标签")
    product_tags: List[str] = Field(default_factory=list, description="商品标签")
    visible_type: Literal["public", "friends", "private"] = Field(default="public", description="可见性")
    allow_comment: bool = Field(default=True, description="允许评论")
    allow_save: bool = Field(default=True, description="允许保存")


# 通用请求响应模型
class LoginRequest(BaseModel):
    """登录请求模型"""
    
    account_name: str = Field(description="账号名称")
    platform: str = Field(description="平台名称")


class LoginResponse(BaseModel):
    """登录响应模型"""
    
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    cookie_file: Optional[str] = Field(default=None, description="Cookie文件路径")
    account: Optional[BaseAccount] = Field(default=None, description="账号信息")


class UploadRequest(BaseModel):
    """上传请求模型"""
    
    account_name: str = Field(description="账号名称")
    platform: str = Field(description="平台名称")
    video_info: BaseVideoInfo = Field(description="视频信息")
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
    platform: str = Field(description="平台名称")
    video_list: List[BaseVideoInfo] = Field(description="视频列表")
    config: BatchUploadConfig = Field(default_factory=BatchUploadConfig, description="批量上传配置")


class BatchUploadResponse(BaseModel):
    """批量上传响应模型"""
    
    success: bool = Field(description="是否成功")
    message: str = Field(description="响应消息")
    total_videos: int = Field(description="总视频数量")
    success_count: int = Field(description="成功上传数量")
    results: List[UploadResponse] = Field(description="详细结果列表")


# Bilibili平台模型
class BilibiliAccount(BaseAccount):
    """Bilibili账号模型"""
    platform: str = "bilibili"


class BilibiliVideoInfo(BaseVideoInfo):
    """Bilibili视频信息"""
    description: Optional[str] = Field(default=None, description="视频简介")
    category: str = Field(default="生活", description="视频分区")
    schedule_time: Optional[datetime] = Field(default=None, description="定时发布时间")
    
    
# 快手平台模型  
class KuaishouAccount(BaseAccount):
    """快手账号模型"""
    platform: str = "kuaishou"


class KuaishouVideoInfo(BaseVideoInfo):
    """快手视频信息"""
    schedule_time: Optional[datetime] = Field(default=None, description="定时发布时间")
    
    
# TikTok平台模型
class TiktokAccount(BaseAccount):
    """TikTok账号模型"""
    platform: str = "tiktok"


class TiktokVideoInfo(BaseVideoInfo):
    """TikTok视频信息"""
    description: Optional[str] = Field(default=None, description="视频描述")
    privacy: Literal["public", "private", "friends"] = Field(default="public", description="隐私设置")
    
    
# YouTube平台模型
class YoutubeAccount(BaseAccount):
    """YouTube账号模型"""
    platform: str = "youtube"


class YoutubeVideoInfo(BaseVideoInfo):
    """YouTube视频信息"""
    description: Optional[str] = Field(default=None, description="视频描述")
    category: str = Field(default="Entertainment", description="视频分类")
    privacy: Literal["public", "unlisted", "private"] = Field(default="public", description="隐私设置")
    schedule_time: Optional[datetime] = Field(default=None, description="定时发布时间")