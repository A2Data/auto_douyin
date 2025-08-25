"""
多平台管理服务
"""

from typing import Dict, List, Optional, Union
from pathlib import Path
import asyncio

from ..models.platforms import (
    BaseAccount, DouyinAccount, WechatChannelAccount, XiaohongshuAccount,
    BaseVideoInfo, DouyinVideoInfo, WechatChannelVideoInfo, XiaohongshuVideoInfo,
    LoginRequest, LoginResponse, UploadRequest, UploadResponse,
    BatchUploadRequest, BatchUploadResponse
)
from ..core.douyin_uploader import DouyinUploader
from ..core.wechat_channel_uploader import WechatChannelUploader  
from ..core.xiaohongshu_uploader import XiaohongshuUploader
from ..utils.logger import logger


class PlatformManager:
    """多平台管理器"""
    
    def __init__(self):
        self.accounts: Dict[str, BaseAccount] = {}
        self.uploaders: Dict[str, Union[DouYinUploader, WechatChannelUploader, XiaohongshuUploader]] = {}
        self.supported_platforms = ["douyin", "wechat_channel", "xiaohongshu"]
        
        # 自动加载已存在的账号信息
        self._load_existing_accounts()
        
    def add_account(self, account: BaseAccount) -> bool:
        """添加账号"""
        try:
            if account.platform not in self.supported_platforms:
                logger.error(f"不支持的平台: {account.platform}")
                return False
                
            account_key = f"{account.platform}_{account.name}"
            self.accounts[account_key] = account
            logger.info(f"已添加账号: {account_key}")
            return True
            
        except Exception as e:
            logger.error(f"添加账号失败: {str(e)}")
            return False
            
    def get_account(self, platform: str, account_name: str) -> Optional[BaseAccount]:
        """获取账号"""
        account_key = f"{platform}_{account_name}"
        return self.accounts.get(account_key)
        
    def list_accounts(self, platform: Optional[str] = None) -> List[BaseAccount]:
        """列出账号"""
        if platform:
            return [account for key, account in self.accounts.items() 
                   if account.platform == platform]
        return list(self.accounts.values())
        
    async def login(self, request: LoginRequest) -> LoginResponse:
        """登录账号"""
        try:
            account = self.get_account(request.platform, request.account_name)
            if not account:
                # 创建新账号
                account = self._create_account(request.platform, request.account_name)
                if not account:
                    return LoginResponse(
                        success=False,
                        message=f"不支持的平台: {request.platform}"
                    )
                    
                self.add_account(account)
                
            # 执行登录（适配不同的接口）
            if request.platform == "douyin":
                # 抖音上传器需要特殊处理
                success = await self._login_douyin(None, account)
            else:
                # 获取对应的上传器
                uploader = await self._get_uploader(request.platform)
                if not uploader:
                    return LoginResponse(
                        success=False,
                        message=f"无法创建{request.platform}上传器"
                    )
                success = await uploader.login(account)
            
            if success:
                account.is_logged_in = True
                return LoginResponse(
                    success=True,
                    message="登录成功",
                    cookie_file=str(account.cookie_file) if account.cookie_file else None,
                    account=account
                )
            else:
                return LoginResponse(
                    success=False,
                    message="登录失败"
                )
                
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return LoginResponse(
                success=False,
                message=f"登录过程出错: {str(e)}"
            )
            
    async def upload_video(self, request: UploadRequest) -> UploadResponse:
        """上传视频"""
        try:
            account = self.get_account(request.platform, request.account_name)
            if not account:
                return UploadResponse(
                    success=False,
                    message=f"账号不存在: {request.account_name}"
                )
                
            if not account.is_logged_in:
                return UploadResponse(
                    success=False,
                    message="账号未登录，请先登录"
                )
                
            # 执行上传（适配不同平台）
            if request.platform == "douyin":
                # 抖音上传器需要特殊处理
                success = await self._upload_douyin(account, request.video_info, request.publish_date)
            else:
                # 获取对应的上传器
                uploader = await self._get_uploader(request.platform)
                if not uploader:
                    return UploadResponse(
                        success=False,
                        message=f"无法创建{request.platform}上传器"
                    )
                    
                # 为上传器加载账号的cookies
                if account.cookie_file and hasattr(uploader, '_load_cookies'):
                    await uploader._load_cookies(account)
                    
                # 转换视频信息为对应平台的格式
                platform_video_info = self._convert_video_info(request.platform, request.video_info)
                if not platform_video_info:
                    return UploadResponse(
                        success=False,
                        message="视频信息格式转换失败"
                    )
                    
                # 执行上传
                success = await uploader.upload_video(platform_video_info)
            
            if success:
                return UploadResponse(
                    success=True,
                    message="视频上传成功",
                    title=platform_video_info.title
                )
            else:
                return UploadResponse(
                    success=False,
                    message="视频上传失败"
                )
                
        except Exception as e:
            logger.error(f"上传视频失败: {str(e)}")
            return UploadResponse(
                success=False,
                message=f"上传过程出错: {str(e)}"
            )
            
    async def batch_upload(self, request: BatchUploadRequest) -> BatchUploadResponse:
        """批量上传视频"""
        try:
            results = []
            success_count = 0
            
            for video_info in request.video_list:
                upload_request = UploadRequest(
                    account_name=request.account_name,
                    platform=request.platform,
                    video_info=video_info
                )
                
                result = await self.upload_video(upload_request)
                results.append(result)
                
                if result.success:
                    success_count += 1
                    
                # 添加延迟避免频率限制
                await asyncio.sleep(5)
                
            return BatchUploadResponse(
                success=success_count > 0,
                message=f"批量上传完成，成功: {success_count}/{len(request.video_list)}",
                total_videos=len(request.video_list),
                success_count=success_count,
                results=results
            )
            
        except Exception as e:
            logger.error(f"批量上传失败: {str(e)}")
            return BatchUploadResponse(
                success=False,
                message=f"批量上传过程出错: {str(e)}",
                total_videos=len(request.video_list),
                success_count=0,
                results=[]
            )
            
    def _create_account(self, platform: str, account_name: str) -> Optional[BaseAccount]:
        """创建账号实例"""
        if platform == "douyin":
            return DouyinAccount(name=account_name)
        elif platform == "wechat_channel":
            return WechatChannelAccount(name=account_name)
        elif platform == "xiaohongshu":
            return XiaohongshuAccount(name=account_name)
        else:
            return None
            
    async def _get_uploader(self, platform: str):
        """获取平台上传器"""
        uploader_key = platform
        
        if uploader_key not in self.uploaders:
            if platform == "douyin":
                # 抖音上传器需要特殊参数，这里先创建占位符
                self.uploaders[uploader_key] = None
            elif platform == "wechat_channel":
                self.uploaders[uploader_key] = WechatChannelUploader()
            elif platform == "xiaohongshu":
                self.uploaders[uploader_key] = XiaohongshuUploader()
            else:
                return None
                
        uploader = self.uploaders[uploader_key]
        
        # 确保上传器已初始化（抖音上传器不需要预先初始化浏览器）
        if platform != "douyin" and hasattr(uploader, 'start_browser'):
            if not hasattr(uploader, 'browser') or not uploader.browser:
                await uploader.start_browser()
            
        return uploader
        
    def _convert_video_info(self, platform: str, video_info: BaseVideoInfo):
        """转换视频信息为平台特定格式"""
        base_data = video_info.model_dump()
        
        if platform == "douyin":
            return DouyinVideoInfo(**base_data)
        elif platform == "wechat_channel":
            return WechatChannelVideoInfo(**base_data)
        elif platform == "xiaohongshu":
            # 小红书需要描述字段
            if 'description' not in base_data or not base_data['description']:
                base_data['description'] = base_data.get('title', '')
            return XiaohongshuVideoInfo(**base_data)
        else:
            return None
            
    async def close_all_uploaders(self):
        """关闭所有上传器"""
        for uploader in self.uploaders.values():
            try:
                await uploader.close_browser()
            except Exception as e:
                logger.error(f"关闭上传器失败: {str(e)}")
                
        self.uploaders.clear()
        logger.info("所有上传器已关闭")
        
    async def _login_douyin(self, uploader, account) -> bool:
        """抖音登录适配方法"""
        try:
            # 创建简单的配置对象（抖音上传器需要config参数）
            from ..models.config import Config
            from pathlib import Path
            
            # 创建基本配置
            config = Config(
                chrome_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                cookies_dir="cookies",
                logs_dir="logs", 
                videos_dir="videos"
            )
            
            # 设置cookie文件路径
            cookie_path = Path(f"cookies/douyin_{account.name}.json")
            
            # 创建抖音上传器实例
            douyin_uploader = DouYinUploader(
                account_name=account.name,
                cookie_file=str(cookie_path),
                config=config
            )
            
            # 更新uploaders字典
            self.uploaders["douyin"] = douyin_uploader
            
            # 执行登录
            success = await douyin_uploader.login()
            
            if success:
                account.cookie_file = cookie_path
            
            return success
            
        except Exception as e:
            logger.error(f"抖音登录适配失败: {str(e)}")
            return False
            
    async def _upload_douyin(self, account, video_info, publish_date=None) -> bool:
        """抖音上传适配方法"""
        try:
            # 获取或创建抖音上传器
            if "douyin" not in self.uploaders or self.uploaders["douyin"] is None:
                # 创建配置对象
                from ..models.config import Config
                config = Config(
                    chrome_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    cookies_dir="cookies",
                    logs_dir="logs", 
                    videos_dir="videos"
                )
                
                # 创建抖音上传器实例
                douyin_uploader = DouYinUploader(
                    account_name=account.name,
                    cookie_file=str(account.cookie_file),
                    config=config
                )
                
                self.uploaders["douyin"] = douyin_uploader
            else:
                douyin_uploader = self.uploaders["douyin"]
            
            # 转换视频信息为抖音格式
            from ..models.douyin import VideoInfo
            douyin_video_info = VideoInfo(
                video_path=video_info.video_path,
                title=video_info.title,
                tags=video_info.tags,
                thumbnail_path=video_info.thumbnail_path,
                location=video_info.location
            )
            
            # 执行上传
            success = await douyin_uploader.upload_video(
                video_info=douyin_video_info,
                publish_date=publish_date
            )
            
            return success
            
        except Exception as e:
            logger.error(f"抖音上传适配失败: {str(e)}")
            return False
    
    def _load_existing_accounts(self):
        """加载已存在的账号信息"""
        try:
            from pathlib import Path
            import os
            
            cookies_dir = Path("cookies")
            if not cookies_dir.exists():
                return
                
            # 扫描cookie文件并创建账号
            for cookie_file in cookies_dir.glob("*.json"):
                filename = cookie_file.stem
                
                # 解析文件名格式: platform_accountname 或 complex_platform_accountname
                if "_" in filename:
                    parts = filename.split("_")
                    
                    # 尝试不同的分割方式
                    platform = None
                    account_name = None
                    
                    # 先尝试找到匹配的平台名称
                    for supported_platform in self.supported_platforms:
                        if filename.startswith(supported_platform + "_"):
                            platform = supported_platform
                            account_name = filename[len(supported_platform) + 1:]
                            break
                    
                    if platform and account_name:
                        # 创建对应的账号对象
                        account = self._create_account(platform, account_name)
                        if account:
                            account.cookie_file = cookie_file
                            account.is_logged_in = True  # 假设有cookie文件就是已登录
                            self.add_account(account)
                            logger.info(f"自动加载账号: {platform}_{account_name}")
                            
        except Exception as e:
            logger.error(f"加载已存在账号失败: {str(e)}")
    
    def get_platform_stats(self) -> Dict[str, int]:
        """获取各平台账号统计"""
        stats = {}
        for platform in self.supported_platforms:
            stats[platform] = len([acc for acc in self.accounts.values() 
                                 if acc.platform == platform])
        return stats