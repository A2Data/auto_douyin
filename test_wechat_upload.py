#!/usr/bin/env python3
"""
测试微信视频号上传功能
基于social-auto-upload优化版本
"""

import asyncio
from pathlib import Path
from src.video_uploader.core.wechat_channel_uploader import WechatChannelUploader
from src.video_uploader.models.platforms import WechatChannelAccount, WechatChannelVideoInfo
from src.video_uploader.utils.logger import logger

async def test_upload():
    """测试上传视频到微信视频号"""
    
    # 创建账号对象
    account = WechatChannelAccount(
        name="wechat",
        cookie_file=Path("cookies/wechat_channel_wechat.json")
    )
    
    # 创建视频信息对象
    video_info = WechatChannelVideoInfo(
        video_path=Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4"),  # 使用实际视频
        title="测试视频上传 - 基于social-auto-upload优化",
        tags=["测试", "自动化"],
        original_statement=True
    )
    
    # 创建上传器并执行上传
    async with WechatChannelUploader(headless=False) as uploader:
        # 登录
        login_success = await uploader.login(account)
        if not login_success:
            logger.error("登录失败")
            return False
        
        logger.info("登录成功，开始上传视频...")
        
        # 上传视频
        upload_success = await uploader.upload_video(video_info)
        if upload_success:
            logger.success("视频上传成功！")
        else:
            logger.error("视频上传失败")
        
        return upload_success

async def main():
    """主函数"""
    try:
        logger.info("=== 开始测试微信视频号上传（优化版） ===")
        
        # 检查测试视频是否存在
        test_video = Path("/Users/jackfeng/Downloads/Vertical_triple_splitscreen_202507112342.mp4")
        if not test_video.exists():
            logger.error(f"测试视频不存在: {test_video}")
            logger.info("请准备一个测试视频文件")
            return
        
        # 执行测试
        success = await test_upload()
        
        if success:
            logger.success("=== 测试完成：上传成功 ===")
        else:
            logger.error("=== 测试完成：上传失败 ===")
            
    except Exception as e:
        logger.error(f"测试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())