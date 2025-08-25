#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多平台视频自动上传服务 - 主入口
支持抖音、微信视频号、小红书等平台
提供FastAPI服务和命令行接口
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from video_uploader import create_app
from video_uploader.models.platforms import (
    LoginRequest, UploadRequest, BaseVideoInfo, BatchUploadRequest
)
from video_uploader.services.platform_manager import PlatformManager
from video_uploader.utils.logger import setup_logging, get_logger

# 设置日志
setup_logging()
logger = get_logger(__name__)


async def run_cli_command(args: argparse.Namespace) -> None:
    """运行CLI命令"""
    # 初始化平台管理器
    platform_manager = PlatformManager()
    
    try:
        if args.action == "login":
            # 登录命令
            request = LoginRequest(
                account_name=args.account,
                platform=args.platform
            )
            result = await platform_manager.login(request)
            print(json.dumps(result.model_dump(mode='json'), indent=2, ensure_ascii=False))
            
        elif args.action == "upload":
            # 上传命令
            if not args.video:
                print(json.dumps({"success": False, "message": "需要指定视频文件路径"}, ensure_ascii=False))
                return
                
            # 解析发布时间
            publish_date = None
            if args.schedule:
                try:
                    publish_date = datetime.strptime(args.schedule, "%Y-%m-%d %H:%M")
                except ValueError:
                    print(json.dumps({"success": False, "message": "日期格式错误，请使用 YYYY-MM-DD HH:MM"}, ensure_ascii=False))
                    return
            
            # 创建视频信息
            video_info = BaseVideoInfo(
                video_path=Path(args.video),
                title=args.title,
                tags=args.tags or [],
                thumbnail_path=Path(args.thumbnail) if args.thumbnail else None,
                location=args.location
            )
            
            request = UploadRequest(
                account_name=args.account,
                platform=args.platform,
                video_info=video_info,
                publish_date=publish_date
            )
            
            result = await platform_manager.upload_video(request)
            print(json.dumps(result.model_dump(mode='json'), indent=2, ensure_ascii=False))
            
        elif args.action == "batch_upload":
            # 批量上传命令
            if not args.batch_config:
                print(json.dumps({"success": False, "message": "需要指定批量上传配置文件路径"}, ensure_ascii=False))
                return
                
            # 读取批量配置
            config_path = Path(args.batch_config)
            if not config_path.exists():
                print(json.dumps({"success": False, "message": f"配置文件不存在: {args.batch_config}"}, ensure_ascii=False))
                return
                
            with open(config_path, 'r', encoding='utf-8') as f:
                batch_config_data = json.load(f)
            
            # 解析视频列表
            video_list = []
            for video_data in batch_config_data.get('video_list', []):
                video_info = BaseVideoInfo(**video_data)
                video_list.append(video_info)
            
            request = BatchUploadRequest(
                account_name=args.account,
                platform=args.platform,
                video_list=video_list
            )
            
            result = await platform_manager.batch_upload(request)
            print(json.dumps(result.model_dump(mode='json'), indent=2, ensure_ascii=False))
            
        elif args.action == "list":
            # 列出账号
            accounts = platform_manager.list_accounts(args.platform)
            account_list = [acc.model_dump(mode='json') for acc in accounts]
            print(json.dumps({"accounts": account_list}, indent=2, ensure_ascii=False))
            
        elif args.action == "stats":
            # 获取平台统计
            stats = platform_manager.get_platform_stats()
            print(json.dumps({"stats": stats}, indent=2, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"执行CLI命令时发生错误: {str(e)}")
        print(json.dumps({"success": False, "message": f"操作失败: {str(e)}"}, ensure_ascii=False))
    finally:
        # 清理资源
        await platform_manager.close_all_uploaders()


def main() -> None:
    """主函数 - 统一入口"""
    parser = argparse.ArgumentParser(description="多平台视频自动上传服务")
    
    # 添加运行模式选择
    subparsers = parser.add_subparsers(dest="mode", help="运行模式")
    
    # 服务器模式
    server_parser = subparsers.add_parser("server", help="启动FastAPI服务器")
    server_parser.add_argument("--host", default="0.0.0.0", help="服务器监听地址")
    server_parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    server_parser.add_argument("--reload", action="store_true", help="开启热重载(开发模式)")
    
    # CLI模式
    cli_parser = subparsers.add_parser("cli", help="运行CLI命令")
    cli_parser.add_argument("action", choices=["login", "upload", "batch_upload", "list", "stats"], help="操作类型")
    cli_parser.add_argument("--platform", choices=["douyin", "wechat_channel", "xiaohongshu"], help="目标平台")
    cli_parser.add_argument("--account", help="账号名称")
    cli_parser.add_argument("--video", help="视频文件路径")
    cli_parser.add_argument("--title", help="视频标题")
    cli_parser.add_argument("--tags", nargs="+", help="话题标签")
    cli_parser.add_argument("--thumbnail", help="缩略图路径")
    cli_parser.add_argument("--schedule", help="定时发布时间 (格式: YYYY-MM-DD HH:MM)")
    cli_parser.add_argument("--location", default="北京市", help="地理位置")
    cli_parser.add_argument("--batch-config", help="批量上传配置文件路径")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        # 启动FastAPI服务器
        app = create_app()
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )
        
    elif args.mode == "cli":
        # 运行CLI命令
        asyncio.run(run_cli_command(args))
        
    else:
        # 默认启动服务器
        logger.info("未指定运行模式，默认启动FastAPI服务器")
        app = create_app()
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()