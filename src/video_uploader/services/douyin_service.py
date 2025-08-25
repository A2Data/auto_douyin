"""抖音服务
负责抖音相关的业务逻辑处理
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from ..core.douyin_uploader import DouyinUploader
from ..models import (
    Config,
    DouyinAccount, 
    VideoInfo,
    LoginRequest,
    LoginResponse,
    UploadRequest,
    UploadResponse,
    BatchUploadRequest,
    BatchUploadResponse,
)
from ..utils.auto_tools import get_title_and_hashtags, generate_schedule_time_next_day
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DouyinService:
    """抖音服务类"""
    
    def __init__(self, config: Config):
        """
        初始化抖音服务
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
    
    async def login(self, request: LoginRequest) -> LoginResponse:
        """
        登录抖音账号并生成Cookie
        
        Args:
            request: 登录请求
            
        Returns:
            LoginResponse: 登录响应
        """
        try:
            cookie_file = self.config.get_cookie_file_path(request.account_name)
            uploader = DouyinUploader(request.account_name, str(cookie_file), self.config)
            
            success = await uploader.login()
            
            if success:
                account = DouyinAccount(
                    name=request.account_name,
                    cookie_file=cookie_file,
                    is_logged_in=True,
                    last_login=datetime.now()
                )
                
                self.logger.info(f"账号 {request.account_name} 登录成功")
                return LoginResponse(
                    success=True,
                    message="登录成功",
                    cookie_file=str(cookie_file),
                    account=account
                )
            else:
                self.logger.error(f"账号 {request.account_name} 登录失败")
                return LoginResponse(success=False, message="登录失败")
                
        except Exception as e:
            self.logger.error(f"登录过程中发生错误: {str(e)}")
            return LoginResponse(success=False, message=f"登录失败: {str(e)}")
    
    async def upload_video(self, request: UploadRequest) -> UploadResponse:
        """
        上传视频到抖音
        
        Args:
            request: 上传请求
            
        Returns:
            UploadResponse: 上传响应
        """
        try:
            video_info = request.video_info
            
            # 如果没有提供标题和标签，尝试从同名txt文件获取
            if not video_info.title or not video_info.tags:
                try:
                    auto_title, auto_tags = get_title_and_hashtags(str(video_info.video_path))
                    if not video_info.title:
                        video_info.title = auto_title
                    if not video_info.tags:
                        video_info.tags = auto_tags
                except Exception:
                    if not video_info.title:
                        video_info.title = video_info.video_path.stem
                    if not video_info.tags:
                        video_info.tags = []
            
            # 创建上传器
            cookie_file = self.config.get_cookie_file_path(request.account_name)
            uploader = DouyinUploader(request.account_name, str(cookie_file), self.config)
            
            # 检查Cookie是否有效
            if not await uploader.check_cookie():
                return UploadResponse(success=False, message="Cookie无效，请重新登录")
            
            # 上传视频
            success = await uploader.upload_video(
                video_path=str(video_info.video_path),
                title=video_info.title,
                tags=video_info.tags,
                thumbnail_path=str(video_info.thumbnail_path) if video_info.thumbnail_path else None,
                publish_date=request.publish_date,
                location=video_info.location
            )
            
            if success:
                self.logger.info(f"视频上传成功: {video_info.title}")
                return UploadResponse(
                    success=True,
                    message="视频上传成功",
                    title=video_info.title
                )
            else:
                self.logger.error(f"视频上传失败: {video_info.title}")
                return UploadResponse(success=False, message="视频上传失败")
                
        except Exception as e:
            self.logger.error(f"上传过程中发生错误: {str(e)}")
            return UploadResponse(success=False, message=f"上传失败: {str(e)}")
    
    async def batch_upload(self, request: BatchUploadRequest) -> BatchUploadResponse:
        """
        批量上传视频
        
        Args:
            request: 批量上传请求
            
        Returns:
            BatchUploadResponse: 批量上传响应
        """
        try:
            config = request.config
            video_list = request.video_list
            
            # 验证配置
            if config.videos_per_day > len(config.daily_times):
                return BatchUploadResponse(
                    success=False,
                    message="每天发布视频数量不能超过可用时间点数量",
                    total_videos=len(video_list),
                    success_count=0,
                    results=[]
                )
            
            # 生成发布时间表
            publish_times = generate_schedule_time_next_day(
                len(video_list),
                config.videos_per_day,
                config.daily_times,
                start_days=config.start_days
            )
            
            results: List[UploadResponse] = []
            for i, video_info in enumerate(video_list):
                publish_date = publish_times[i] if i < len(publish_times) else None
                
                upload_request = UploadRequest(
                    account_name=request.account_name,
                    video_info=video_info,
                    publish_date=publish_date
                )
                
                result = await self.upload_video(upload_request)
                results.append(result)
                
                # 添加延迟避免频繁操作
                await asyncio.sleep(2)
            
            success_count = sum(1 for r in results if r.success)
            
            self.logger.info(f"批量上传完成: {success_count}/{len(video_list)} 成功")
            return BatchUploadResponse(
                success=True,
                message=f"批量上传完成: {success_count}/{len(video_list)} 成功",
                total_videos=len(video_list),
                success_count=success_count,
                results=results
            )
            
        except Exception as e:
            self.logger.error(f"批量上传过程中发生错误: {str(e)}")
            return BatchUploadResponse(
                success=False,
                message=f"批量上传失败: {str(e)}",
                total_videos=len(request.video_list),
                success_count=0,
                results=[]
            )
    
    async def check_account_status(self, account_name: str) -> DouyinAccount:
        """
        检查账号状态
        
        Args:
            account_name: 账号名称
            
        Returns:
            DouyinAccount: 账号信息
        """
        cookie_file = self.config.get_cookie_file_path(account_name)
        
        if not cookie_file.exists():
            return DouyinAccount(
                name=account_name,
                cookie_file=cookie_file,
                is_logged_in=False
            )
        
        try:
            uploader = DouyinUploader(account_name, str(cookie_file), self.config)
            is_valid = await uploader.check_cookie()
            
            return DouyinAccount(
                name=account_name,
                cookie_file=cookie_file,
                is_logged_in=is_valid
            )
        except Exception as e:
            self.logger.error(f"检查账号状态失败: {e}")
            return DouyinAccount(
                name=account_name,
                cookie_file=cookie_file,
                is_logged_in=False
            )
