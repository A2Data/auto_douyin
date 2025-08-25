"""
快手视频上传器
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from playwright.async_api import Browser, Page, async_playwright
from ..models.platforms import KuaishouAccount, KuaishouVideoInfo
from ..utils.logger import logger


class KuaishouUploader:
    """快手上传器"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.current_account: Optional[KuaishouAccount] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_browser()
        
    async def start_browser(self):
        """启动浏览器"""
        playwright = await async_playwright().start()
        
        # 检测系统Chrome路径
        chrome_path = self._get_chrome_path()
        
        launch_options = {
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--lang=en-GB'
            ]
        }
        
        if chrome_path and not self.headless:
            launch_options['executable_path'] = chrome_path
            logger.info(f"使用系统Chrome: {chrome_path}")
        
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # 创建上下文
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = await context.new_page()
        
        # 添加反检测脚本
        await self._add_stealth_script()
        
        logger.info("浏览器启动成功")
        
    def _get_chrome_path(self):
        """获取系统Chrome路径"""
        import platform
        system = platform.system()
        
        if system == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
            ]
        elif system == "Windows":
            chrome_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            ]
        else:  # Linux
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium",
            ]
        
        for path in chrome_paths:
            if Path(path).exists():
                return path
        
        return None
        
    async def _add_stealth_script(self):
        """添加反检测脚本"""
        stealth_script = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        window.chrome = {
            runtime: {},
        };
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        """
        
        await self.page.add_init_script(stealth_script)
        
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")
            
    async def login(self, account: KuaishouAccount) -> bool:
        """登录快手"""
        try:
            logger.info(f"开始登录快手账号: {account.name}")
            self.current_account = account
            
            # 先尝试加载已保存的cookies
            if await self._load_cookies(account):
                logger.info("正在验证已保存的登录状态...")
                
            # 访问快手创作者中心
            await self.page.goto("https://cp.kuaishou.com/article/publish/video")
            await asyncio.sleep(3)
            
            # 验证登录状态
            if await self._verify_login_status():
                self.is_logged_in = True
                logger.info("使用已保存的登录状态")
                return True
            
            # 需要登录
            logger.info("需要登录，请扫码登录")
            logger.info("请在弹出的浏览器窗口中扫码登录")
            
            # 跳转到登录页
            await self.page.goto("https://cp.kuaishou.com")
            
            # 等待登录完成
            success = await self._wait_for_login_success()
            if success:
                await self._save_cookies(account)
                self.is_logged_in = True
                logger.info("登录成功")
                return True
            else:
                logger.error("登录失败或超时")
                return False
                
        except Exception as e:
            logger.error(f"登录过程出错: {str(e)}")
            return False
            
    async def _verify_login_status(self) -> bool:
        """验证登录状态"""
        try:
            # 等待页面加载
            await self.page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)
            # 如果找到"机构服务"说明未登录
            return False
        except:
            # 超时说明已登录
            return True
            
    async def _wait_for_login_success(self, timeout: int = 300) -> bool:
        """等待登录成功"""
        try:
            await self.page.wait_for_url("**/article/publish/**", timeout=timeout * 1000)
            await asyncio.sleep(2)
            return True
        except:
            return False
            
    async def _save_cookies(self, account: KuaishouAccount):
        """保存cookies"""
        try:
            cookies = await self.page.context.cookies()
            
            # 确保cookies目录存在
            cookies_dir = Path("cookies")
            cookies_dir.mkdir(exist_ok=True)
            
            cookie_file = cookies_dir / f"kuaishou_{account.name}.json"
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
                
            account.cookie_file = cookie_file
            logger.info(f"Cookies已保存: {cookie_file}")
            
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            
    async def _load_cookies(self, account: KuaishouAccount) -> bool:
        """加载cookies"""
        try:
            if not account.cookie_file or not account.cookie_file.exists():
                return False
                
            with open(account.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                
            await self.page.context.add_cookies(cookies)
            logger.info(f"Cookies已加载: {account.cookie_file}")
            return True
            
        except Exception as e:
            logger.error(f"加载cookies失败: {str(e)}")
            return False
            
    async def upload_video(self, video_info: KuaishouVideoInfo) -> bool:
        """上传视频到快手"""
        try:
            if not self.is_logged_in:
                logger.error("未登录，请先登录")
                return False
                
            logger.info(f"[+]正在上传视频到快手: {video_info.title}")
            
            # 访问上传页面
            await self.page.goto("https://cp.kuaishou.com/article/publish/video")
            logger.info('  [-] 正在打开主页...')
            await self.page.wait_for_url("https://cp.kuaishou.com/article/publish/video")
            
            # 点击上传视频按钮
            logger.info("  [-] 正在选择视频文件...")
            await self.page.locator('div[class^="upload-btn"] input').set_input_files(str(video_info.video_path))
            
            # 等待页面跳转到发布页面
            await self.page.wait_for_url("https://cp.kuaishou.com/article/publish/video?**")
            logger.info("  [-] 进入视频发布页面")
            
            # 填写标题
            await self._fill_title(video_info.title)
            
            # 添加话题标签
            await self._add_tags(video_info.tags)
            
            # 设置封面
            if video_info.thumbnail_path:
                await self._set_thumbnail(video_info.thumbnail_path)
            
            # 等待视频上传完成
            await self._wait_video_upload()
            
            # 设置定时发布（如果需要）
            if video_info.schedule_time:
                await self._set_schedule_time(video_info.schedule_time)
            
            # 发布视频
            return await self._publish_video()
            
        except Exception as e:
            logger.error(f"上传视频失败: {str(e)}")
            return False
            
    async def _fill_title(self, title: str):
        """填写标题"""
        try:
            # 查找标题输入框
            title_input = self.page.locator('div[class^="video-title"] textarea')
            await title_input.click()
            await title_input.fill(title[:30])  # 快手标题限制30字
            logger.info(f"  [-] 已填写标题: {title[:30]}")
        except Exception as e:
            logger.error(f"填写标题失败: {str(e)}")
            
    async def _add_tags(self, tags: List[str]):
        """添加话题标签"""
        try:
            if not tags:
                return
                
            # 点击添加话题
            await self.page.locator('div[class^="tag-btn"]').click()
            await asyncio.sleep(1)
            
            for tag in tags[:5]:  # 快手最多5个标签
                # 输入标签
                tag_input = self.page.locator('div[class^="tag-input"] input')
                await tag_input.fill(tag)
                await asyncio.sleep(1)
                
                # 选择第一个推荐
                first_suggestion = self.page.locator('div[class^="tag-suggestion"] div[class^="tag-item"]').first
                if await first_suggestion.count():
                    await first_suggestion.click()
                    
            logger.info(f"  [-] 已添加{len(tags[:5])}个标签")
        except Exception as e:
            logger.error(f"添加标签失败: {str(e)}")
            
    async def _set_thumbnail(self, thumbnail_path: Path):
        """设置封面"""
        try:
            # 点击设置封面
            await self.page.locator('div[class^="cover-btn"]').click()
            await asyncio.sleep(1)
            
            # 上传封面图片
            await self.page.locator('input[type="file"][accept*="image"]').set_input_files(str(thumbnail_path))
            await asyncio.sleep(2)
            
            # 确认封面
            await self.page.locator('button:has-text("确定")').click()
            logger.info("  [-] 封面设置完成")
        except Exception as e:
            logger.error(f"设置封面失败: {str(e)}")
            
    async def _wait_video_upload(self):
        """等待视频上传完成"""
        try:
            logger.info("  [-] 正在上传视频中...")
            
            # 等待上传进度条消失或显示100%
            while True:
                # 检查是否有进度条
                progress_bar = self.page.locator('div[class*="progress"]')
                if await progress_bar.count() == 0:
                    logger.info("  [-] 视频上传完毕")
                    break
                    
                # 检查进度
                progress_text = await progress_bar.inner_text()
                if "100%" in progress_text or "完成" in progress_text:
                    logger.info("  [-] 视频上传完毕")
                    break
                    
                logger.info(f"  [-] 上传进度: {progress_text}")
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"等待上传完成时出错: {str(e)}")
            
    async def _set_schedule_time(self, schedule_time: datetime):
        """设置定时发布"""
        try:
            # 点击定时发布
            await self.page.locator('label:has-text("定时发布")').click()
            await asyncio.sleep(1)
            
            # 输入时间
            time_str = schedule_time.strftime("%Y-%m-%d %H:%M")
            time_input = self.page.locator('input[placeholder*="时间"]')
            await time_input.click()
            await time_input.fill(time_str)
            await self.page.keyboard.press("Enter")
            
            logger.info(f"  [-] 已设置定时发布: {time_str}")
        except Exception as e:
            logger.error(f"设置定时发布失败: {str(e)}")
            
    async def _publish_video(self) -> bool:
        """发布视频"""
        try:
            # 点击发布按钮
            publish_button = self.page.locator('button[class*="publish"]:has-text("发布")')
            if await publish_button.count() == 0:
                publish_button = self.page.locator('button:has-text("发布")')
                
            await publish_button.click()
            logger.info("  [-] 已点击发布按钮")
            
            # 等待发布完成
            await asyncio.sleep(3)
            
            # 检查是否跳转到作品管理页面
            current_url = self.page.url
            if "manage" in current_url or "content" in current_url:
                logger.success("  [-] 视频发布成功！")
                
                # 保存cookies
                await self._save_cookies(self.current_account)
                logger.info("  [-] Cookie已更新")
                
                return True
            else:
                logger.info("  [-] 等待发布完成...")
                await asyncio.sleep(5)
                return True
                
        except Exception as e:
            logger.error(f"发布视频失败: {str(e)}")
            return False