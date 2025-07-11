#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Douyin Upload MCP Server
独立的抖音上传MCP服务
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import argparse

from douyin_uploader import DouYinUploader
from config import Config, setup_config
from logger import get_logger, setup_logging
from utils import get_title_and_hashtags, generate_schedule_time_next_day

# 设置日志
setup_logging()
logger = get_logger(__name__)


class DouyinMCPService:
    """抖音MCP服务类"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

    async def login(self, account_name: str) -> Dict[str, Any]:
        """
        登录抖音账号并生成Cookie
        
        Args:
            account_name: 账号名称
            
        Returns:
            Dict包含操作结果
        """
        try:
            cookie_file = self.config.get_cookie_file_path(account_name)
            uploader = DouYinUploader(account_name, cookie_file, self.config)

            success = await uploader.login()

            if success:
                self.logger.info(f"账号 {account_name} 登录成功")
                return {"success": True, "message": "登录成功", "cookie_file": str(cookie_file)}
            else:
                self.logger.error(f"账号 {account_name} 登录失败")
                return {"success": False, "message": "登录失败"}

        except Exception as e:
            self.logger.error(f"登录过程中发生错误: {str(e)}")
            return {"success": False, "message": f"登录失败: {str(e)}"}

    async def upload_video(self,
                           account_name: str,
                           video_path: str,
                           title: str = None,
                           tags: List[str] = None,
                           thumbnail_path: str = None,
                           publish_date: datetime = None,
                           location: str = "杭州市") -> Dict[str, Any]:
        """
        上传视频到抖音
        
        Args:
            account_name: 账号名称
            video_path: 视频文件路径
            title: 视频标题
            tags: 话题标签列表
            thumbnail_path: 缩略图路径
            publish_date: 发布时间(None表示立即发布)
            location: 地理位置
            
        Returns:
            Dict包含操作结果
        """
        try:
            # 验证文件存在
            video_file = Path(video_path)
            if not video_file.exists():
                return {"success": False, "message": f"视频文件不存在: {video_path}"}

            # 如果没有提供标题和标签，尝试从同名txt文件获取
            if not title or not tags:
                try:
                    auto_title, auto_tags = get_title_and_hashtags(video_path)
                    title = title or auto_title
                    tags = tags or auto_tags
                except:
                    title = title or video_file.stem
                    tags = tags or []

            # 创建上传器
            cookie_file = self.config.get_cookie_file_path(account_name)
            uploader = DouYinUploader(account_name, cookie_file, self.config)

            # 检查Cookie是否有效
            if not await uploader.check_cookie():
                return {"success": False, "message": "Cookie无效，请重新登录"}

            # 上传视频
            success = await uploader.upload_video(
                video_path=video_path,
                title=title,
                tags=tags,
                thumbnail_path=thumbnail_path,
                publish_date=publish_date,
                location=location
            )

            if success:
                self.logger.info(f"视频上传成功: {title}")
                return {"success": True, "message": "视频上传成功", "title": title}
            else:
                self.logger.error(f"视频上传失败: {title}")
                return {"success": False, "message": "视频上传失败"}

        except Exception as e:
            self.logger.error(f"上传过程中发生错误: {str(e)}")
            return {"success": False, "message": f"上传失败: {str(e)}"}

    async def batch_upload(self,
                           account_name: str,
                           video_list: List[Dict[str, Any]],
                           videos_per_day: int = 1,
                           daily_times: List[int] = None,
                           start_days: int = 0) -> Dict[str, Any]:
        """
        批量上传视频
        
        Args:
            account_name: 账号名称
            video_list: 视频列表，每个元素包含video_path, title, tags等信息
            videos_per_day: 每天上传视频数量
            daily_times: 每天上传的时间点
            start_days: 从几天后开始上传
            
        Returns:
            Dict包含操作结果
        """
        try:
            # 生成发布时间表
            if daily_times is None:
                daily_times = [9, 12, 15, 18, 21]

            publish_times = generate_schedule_time_next_day(
                len(video_list),
                videos_per_day,
                daily_times,
                start_days=start_days
            )

            results = []
            for i, video_info in enumerate(video_list):
                video_path = video_info.get('video_path')
                title = video_info.get('title')
                tags = video_info.get('tags', [])
                thumbnail_path = video_info.get('thumbnail_path')
                publish_date = publish_times[i] if i < len(publish_times) else None

                result = await self.upload_video(
                    account_name=account_name,
                    video_path=video_path,
                    title=title,
                    tags=tags,
                    thumbnail_path=thumbnail_path,
                    publish_date=publish_date
                )
                results.append(result)

                # 添加延迟避免频繁操作
                await asyncio.sleep(2)

            success_count = sum(1 for r in results if r.get('success'))

            self.logger.info(f"批量上传完成: {success_count}/{len(video_list)} 成功")
            return {
                "success": True,
                "message": f"批量上传完成: {success_count}/{len(video_list)} 成功",
                "results": results
            }

        except Exception as e:
            self.logger.error(f"批量上传过程中发生错误: {str(e)}")
            return {"success": False, "message": f"批量上传失败: {str(e)}"}


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="抖音自动上传MCP服务")
    parser.add_argument("action", choices=["login", "upload", "batch_upload"], help="操作类型")
    parser.add_argument("--account", required=True, help="账号名称")
    parser.add_argument("--video", help="视频文件路径")
    parser.add_argument("--title", help="视频标题")
    parser.add_argument("--tags", nargs="+", help="话题标签")
    parser.add_argument("--thumbnail", help="缩略图路径")
    parser.add_argument("--schedule", help="定时发布时间 (格式: YYYY-MM-DD HH:MM)")
    parser.add_argument("--location", default="北京市", help="地理位置")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--batch-config", help="批量上传配置文件路径")

    args = parser.parse_args()

    # 设置配置
    config = setup_config(args.config)
    service = DouyinMCPService(config)

    try:
        if args.action == "login":
            result = await service.login(args.account)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.action == "upload":
            if not args.video:
                print(json.dumps({"success": False, "message": "需要指定视频文件路径"}, ensure_ascii=False))
                return

            publish_date = None
            if args.schedule:
                try:
                    publish_date = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")
                except ValueError:
                    print(
                        json.dumps(
                            {"success": False, "message": "日期格式错误，请使用 YYYY-MM-DD HH:MM"}, ensure_ascii=False
                        )
                    )
                    return

            result = await service.upload_video(
                account_name=args.account,
                video_path=args.video,
                title=args.title,
                tags=args.tags,
                thumbnail_path=args.thumbnail,
                publish_date=publish_date,
                location=args.location
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.action == "batch_upload":
            if not args.batch_config:
                print(json.dumps({"success": False, "message": "需要指定批量上传配置文件路径"}, ensure_ascii=False))
                return

            # 读取批量配置
            with open(args.batch_config, 'r', encoding='utf-8') as f:
                batch_config = json.load(f)

            result = await service.batch_upload(
                account_name=args.account,
                video_list=batch_config.get('video_list', []),
                videos_per_day=batch_config.get('videos_per_day', 1),
                daily_times=batch_config.get('daily_times', [9, 12, 15, 18, 21]),
                start_days=batch_config.get('start_days', 0)
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.error(f"执行操作时发生错误: {str(e)}")
        print(json.dumps({"success": False, "message": f"操作失败: {str(e)}"}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
