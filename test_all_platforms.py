#!/usr/bin/env python3
"""
测试所有平台的上传功能
"""

import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from src.video_uploader.core import (
    DouyinUploader,
    WechatChannelUploader,
    XiaohongshuUploader,
    BilibiliUploader,
    KuaishouUploader
)
from src.video_uploader.models.platforms import (
    DouyinAccount, DouyinVideoInfo,
    WechatChannelAccount, WechatChannelVideoInfo,
    XiaohongshuAccount, XiaohongshuVideoInfo,
    BilibiliAccount, BilibiliVideoInfo,
    KuaishouAccount, KuaishouVideoInfo
)
from src.video_uploader.utils.logger import logger


async def test_douyin():
    """测试抖音上传"""
    logger.info("=== 测试抖音上传 ===")
    
    account = DouyinAccount(
        name="test",
        cookie_file=Path("cookies/douyin_test.json")
    )
    
    video_info = DouyinVideoInfo(
        video_path=Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4"),
        title="测试抖音上传 - MCP Server",
        tags=["测试", "自动化"],
        location="北京市"
    )
    
    async with DouyinUploader(headless=False) as uploader:
        login_success = await uploader.login(account)
        if login_success:
            logger.info("抖音登录成功")
            upload_success = await uploader.upload_video(video_info)
            if upload_success:
                logger.success("抖音视频上传成功！")
            else:
                logger.error("抖音视频上传失败")
        else:
            logger.error("抖音登录失败")


async def test_wechat():
    """测试微信视频号上传"""
    logger.info("=== 测试微信视频号上传 ===")
    
    account = WechatChannelAccount(
        name="wechat",
        cookie_file=Path("cookies/wechat_channel_wechat.json")
    )
    
    video_info = WechatChannelVideoInfo(
        video_path=Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4"),
        title="测试微信视频号上传 - MCP Server",
        tags=["测试", "自动化"],
        original_statement=True
    )
    
    async with WechatChannelUploader(headless=False) as uploader:
        login_success = await uploader.login(account)
        if login_success:
            logger.info("微信视频号登录成功")
            upload_success = await uploader.upload_video(video_info)
            if upload_success:
                logger.success("微信视频号上传成功！")
            else:
                logger.error("微信视频号上传失败")
        else:
            logger.error("微信视频号登录失败")


async def test_xiaohongshu():
    """测试小红书上传"""
    logger.info("=== 测试小红书上传 ===")
    
    account = XiaohongshuAccount(
        name="xhs",
        cookie_file=Path("cookies/xiaohongshu_xhs.json")
    )
    
    video_info = XiaohongshuVideoInfo(
        video_path=Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4"),
        title="测试小红书上传 - MCP Server",
        tags=["测试", "自动化"],
        description="这是一个测试视频"
    )
    
    async with XiaohongshuUploader(headless=False) as uploader:
        login_success = await uploader.login(account)
        if login_success:
            logger.info("小红书登录成功")
            upload_success = await uploader.upload_video(video_info)
            if upload_success:
                logger.success("小红书视频上传成功！")
            else:
                logger.error("小红书视频上传失败")
        else:
            logger.error("小红书登录失败")


async def test_bilibili():
    """测试B站上传"""
    logger.info("=== 测试B站上传 ===")
    
    account = BilibiliAccount(
        name="bilibili",
        cookie_file=Path("cookies/bilibili_test.json")
    )
    
    video_info = BilibiliVideoInfo(
        video_path=Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4"),
        title="测试B站上传 - MCP Server",
        tags=["测试", "自动化"],
        category="生活",
        description="这是一个测试视频"
    )
    
    async with BilibiliUploader() as uploader:
        login_success = await uploader.login(account)
        if login_success:
            logger.info("B站登录成功")
            upload_success = await uploader.upload_video(video_info)
            if upload_success:
                logger.success("B站视频上传成功！")
            else:
                logger.error("B站视频上传失败")
        else:
            logger.error("B站登录失败，请先获取cookie")


async def test_kuaishou():
    """测试快手上传"""
    logger.info("=== 测试快手上传 ===")
    
    account = KuaishouAccount(
        name="kuaishou",
        cookie_file=Path("cookies/kuaishou_test.json")
    )
    
    video_info = KuaishouVideoInfo(
        video_path=Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4"),
        title="测试快手上传 - MCP Server",
        tags=["测试", "自动化"]
    )
    
    async with KuaishouUploader(headless=False) as uploader:
        login_success = await uploader.login(account)
        if login_success:
            logger.info("快手登录成功")
            upload_success = await uploader.upload_video(video_info)
            if upload_success:
                logger.success("快手视频上传成功！")
            else:
                logger.error("快手视频上传失败")
        else:
            logger.error("快手登录失败")


async def main():
    """主函数"""
    logger.info("===== 开始测试所有平台 =====")
    
    # 选择要测试的平台
    print("\n请选择要测试的平台：")
    print("1. 抖音")
    print("2. 微信视频号")
    print("3. 小红书")
    print("4. B站")
    print("5. 快手")
    print("6. 测试所有平台")
    
    choice = input("\n请输入选项 (1-6): ").strip()
    
    if choice == "1":
        await test_douyin()
    elif choice == "2":
        await test_wechat()
    elif choice == "3":
        await test_xiaohongshu()
    elif choice == "4":
        await test_bilibili()
    elif choice == "5":
        await test_kuaishou()
    elif choice == "6":
        # 测试所有平台
        platforms = [
            ("微信视频号", test_wechat),
            ("抖音", test_douyin),
            ("小红书", test_xiaohongshu),
            ("B站", test_bilibili),
            ("快手", test_kuaishou)
        ]
        
        for platform_name, test_func in platforms:
            try:
                logger.info(f"\n开始测试 {platform_name}...")
                await test_func()
                logger.info(f"{platform_name} 测试完成\n")
            except Exception as e:
                logger.error(f"{platform_name} 测试失败: {str(e)}\n")
            
            # 平台间延迟
            await asyncio.sleep(3)
    else:
        logger.error("无效的选项")
    
    logger.info("===== 测试完成 =====")


if __name__ == "__main__":
    asyncio.run(main())