"""
Bilibili视频上传器
基于biliup库实现
"""

import json
import random
from pathlib import Path
from typing import Optional, List, Dict

from ..models.platforms import BilibiliAccount, BilibiliVideoInfo
from ..utils.logger import logger


class BilibiliUploader:
    """Bilibili上传器"""
    
    # B站分区ID映射
    TID_MAP = {
        "动画": 1,
        "番剧": 13,
        "国创": 167,
        "音乐": 3,
        "舞蹈": 129,
        "游戏": 4,
        "知识": 36,
        "科技": 188,
        "运动": 234,
        "汽车": 223,
        "生活": 160,
        "美食": 211,
        "动物圈": 217,
        "鬼畜": 119,
        "时尚": 155,
        "娱乐": 5,
        "影视": 181,
        "纪录片": 177,
        "电影": 23,
        "电视剧": 11,
    }
    
    def __init__(self):
        self.is_logged_in = False
        self.current_account: Optional[BilibiliAccount] = None
        self.bili_client = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        pass
        
    def _extract_cookies_from_file(self, cookie_file: Path) -> Dict:
        """从cookie文件提取B站需要的字段"""
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # B站需要的关键cookie字段
            keys_to_extract = ["SESSDATA", "bili_jct", "DedeUserID__ckMd5", "DedeUserID", "access_token"]
            extracted_data = {}
            
            # 如果是标准cookie格式
            if isinstance(data, list):
                for cookie in data:
                    if cookie.get('name') in keys_to_extract:
                        extracted_data[cookie['name']] = cookie['value']
            # 如果是B站特殊格式
            elif isinstance(data, dict):
                if 'cookie_info' in data:
                    for cookie in data['cookie_info'].get('cookies', []):
                        if cookie['name'] in keys_to_extract:
                            extracted_data[cookie['name']] = cookie['value']
                if 'token_info' in data and 'access_token' in data['token_info']:
                    extracted_data['access_token'] = data['token_info']['access_token']
                # 直接的键值对
                for key in keys_to_extract:
                    if key in data:
                        extracted_data[key] = data[key]
                        
            return extracted_data
            
        except Exception as e:
            logger.error(f"解析B站cookie失败: {str(e)}")
            return {}
            
    async def login(self, account: BilibiliAccount) -> bool:
        """登录B站"""
        try:
            logger.info(f"开始登录B站账号: {account.name}")
            self.current_account = account
            
            # 加载cookie
            if not account.cookie_file or not account.cookie_file.exists():
                logger.error(f"Cookie文件不存在: {account.cookie_file}")
                logger.info("请先通过浏览器登录B站并保存cookie")
                return False
            
            # 提取cookie数据
            cookie_data = self._extract_cookies_from_file(account.cookie_file)
            if not cookie_data:
                logger.error("无法提取有效的cookie数据")
                return False
            
            # 尝试导入biliup库
            try:
                from biliup.plugins.bili_webup import BiliBili, Data
                self.BiliBili = BiliBili
                self.Data = Data
            except ImportError:
                logger.error("未安装biliup库，请运行: pip install biliup")
                return False
            
            # 验证登录状态
            try:
                data = self.Data()
                with self.BiliBili(data) as bili:
                    bili.login_by_cookies(cookie_data)
                    bili.access_token = cookie_data.get('access_token')
                    # 简单验证登录状态
                    self.is_logged_in = True
                    logger.info("B站登录成功")
                    return True
            except Exception as e:
                logger.error(f"B站登录验证失败: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"登录B站过程出错: {str(e)}")
            return False
            
    async def upload_video(self, video_info: BilibiliVideoInfo) -> bool:
        """上传视频到B站"""
        try:
            if not self.is_logged_in:
                logger.error("未登录B站，请先登录")
                return False
            
            logger.info(f"[+] 开始上传视频到B站: {video_info.title}")
            
            # 获取分区ID
            tid = self.TID_MAP.get(video_info.category, 160)  # 默认生活分区
            
            # 准备上传数据
            data = self.Data()
            data.copyright = 1  # 1=自制, 2=转载
            data.title = video_info.title[:80]  # B站标题限制80字符
            data.desc = video_info.description or self._generate_desc(video_info)
            data.tid = tid
            data.set_tag(video_info.tags[:10])  # B站最多10个标签
            
            # 设置定时发布
            if video_info.schedule_time:
                import time
                data.dtime = int(video_info.schedule_time.timestamp())
            else:
                data.dtime = 0  # 立即发布
            
            # 获取cookie数据
            cookie_data = self._extract_cookies_from_file(self.current_account.cookie_file)
            
            # 执行上传
            with self.BiliBili(data) as bili:
                bili.login_by_cookies(cookie_data)
                bili.access_token = cookie_data.get('access_token')
                
                # 上传视频文件
                logger.info("  [-] 正在上传视频文件...")
                video_part = bili.upload_file(
                    str(video_info.video_path), 
                    lines='AUTO',  # 自动选择线路
                    tasks=3  # 上传线程数
                )
                
                video_part['title'] = video_info.title
                data.append(video_part)
                
                # 上传封面（如果有）
                if video_info.thumbnail_path and video_info.thumbnail_path.exists():
                    logger.info("  [-] 正在上传封面...")
                    cover_url = bili.upload_cover(str(video_info.thumbnail_path))
                    data.cover = cover_url
                
                # 提交视频
                logger.info("  [-] 正在提交视频...")
                ret = bili.submit()
                
                if ret.get('code') == 0:
                    logger.success(f"  [-] 视频上传成功！BV号: {ret.get('data', {}).get('bvid', '')}")
                    return True
                else:
                    logger.error(f"  [-] 视频上传失败: {ret.get('message', '未知错误')}")
                    return False
                    
        except ImportError:
            logger.error("缺少biliup依赖，请安装: pip install biliup")
            return False
        except Exception as e:
            logger.error(f"上传视频到B站失败: {str(e)}")
            return False
            
    def _generate_desc(self, video_info: BilibiliVideoInfo) -> str:
        """生成视频简介"""
        desc_parts = []
        
        # 添加标题
        desc_parts.append(video_info.title)
        desc_parts.append("")
        
        # 添加标签
        if video_info.tags:
            desc_parts.append("标签：" + " ".join([f"#{tag}" for tag in video_info.tags]))
            desc_parts.append("")
        
        # 添加随机emoji装饰
        emoji = self._random_emoji()
        desc_parts.append(f"{emoji} 感谢观看 {emoji}")
        
        return "\n".join(desc_parts)
        
    def _random_emoji(self) -> str:
        """获取随机emoji"""
        emoji_list = [
            "🎬", "📹", "🎥", "📺", "🎮", "🎯", "🎨", "🎭", "🎪", "🎸",
            "🎵", "🎶", "🎼", "🎤", "🎧", "🎹", "🥁", "🎺", "🎻", "🪕",
            "🌟", "⭐", "✨", "💫", "🌈", "🌸", "🌺", "🌻", "🌹", "🌷",
            "🍀", "🌿", "🍃", "🌱", "🌴", "🌵", "🦋", "🐝", "🐞", "🦜",
            "🚀", "✈️", "🛸", "🎆", "🎇", "🎉", "🎊", "🎈", "🎁", "🏆"
        ]
        return random.choice(emoji_list)