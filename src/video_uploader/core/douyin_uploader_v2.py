"""
抖音视频上传器 - 优化版
基于最新的抖音创作者中心页面结构
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from playwright.async_api import Browser, Page, async_playwright
from ..models.platforms import DouyinAccount, DouyinVideoInfo
from ..utils.logger import logger


class DouyinUploader:
    """抖音上传器 - 优化版"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.current_account: Optional[DouyinAccount] = None
        
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
            
    async def login(self, account: DouyinAccount) -> bool:
        """登录抖音"""
        try:
            logger.info(f"开始登录抖音账号: {account.name}")
            self.current_account = account
            
            # 先尝试加载已保存的cookies
            if await self._load_cookies(account):
                logger.info("正在验证已保存的登录状态...")
                
            # 访问抖音创作者中心
            await self.page.goto("https://creator.douyin.com/creator-micro/content/upload")
            await asyncio.sleep(3)
            
            # 验证登录状态
            if await self._verify_login_status():
                self.is_logged_in = True
                logger.info("使用已保存的登录状态")
                return True
            
            # 检查是否需要登录
            if await self._need_login():
                logger.info("需要登录，请使用手机抖音扫码")
                logger.info("请在弹出的浏览器窗口中扫码登录")
                
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
            
            return False
                
        except Exception as e:
            logger.error(f"登录过程出错: {str(e)}")
            return False
            
    async def _need_login(self) -> bool:
        """检查是否需要登录"""
        try:
            # 检查是否有登录相关元素
            if await self.page.get_by_text('手机号登录').count() or \
               await self.page.get_by_text('扫码登录').count():
                return True
            return False
        except:
            return True
            
    async def _wait_for_login_success(self, timeout: int = 300) -> bool:
        """等待登录成功"""
        try:
            await self.page.wait_for_url("**/creator-micro/content/**", timeout=timeout * 1000)
            await asyncio.sleep(2)
            return True
        except:
            return False
            
    async def _verify_login_status(self) -> bool:
        """验证登录状态"""
        try:
            await self.page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
            
            # 检查是否有登录按钮
            if await self.page.get_by_text('手机号登录').count() or \
               await self.page.get_by_text('扫码登录').count():
                return False
            
            return True
        except:
            return False
            
    async def _save_cookies(self, account: DouyinAccount):
        """保存cookies"""
        try:
            cookies = await self.page.context.cookies()
            
            # 确保cookies目录存在
            cookies_dir = Path("cookies")
            cookies_dir.mkdir(exist_ok=True)
            
            cookie_file = cookies_dir / f"douyin_{account.name}.json"
            
            import json
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
                
            account.cookie_file = cookie_file
            logger.info(f"Cookies已保存: {cookie_file}")
            
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            
    async def _load_cookies(self, account: DouyinAccount) -> bool:
        """加载cookies"""
        try:
            if not account.cookie_file or not account.cookie_file.exists():
                return False
                
            import json
            with open(account.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                
            await self.page.context.add_cookies(cookies)
            logger.info(f"Cookies已加载: {account.cookie_file}")
            return True
            
        except Exception as e:
            logger.error(f"加载cookies失败: {str(e)}")
            return False
            
    async def upload_video(self, video_info: DouyinVideoInfo) -> bool:
        """上传视频"""
        try:
            if not self.is_logged_in:
                logger.error("未登录，请先登录")
                return False
                
            logger.info(f"[+]正在上传-------{video_info.title}.mp4")
            
            # 访问上传页面
            await self.page.goto("https://creator.douyin.com/creator-micro/content/upload")
            await self.page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")
            
            # 上传视频文件
            logger.info("[-] 正在选择视频文件...")
            await self.page.locator("div[class^='container'] input").set_input_files(str(video_info.video_path))
            
            # 等待跳转到发布页面（兼容两种页面）
            await self._wait_for_publish_page()
            
            # 填写视频信息
            await self._fill_video_info(video_info)
            
            # 等待视频上传完成
            await self._wait_video_upload()
            
            # 设置封面
            if video_info.thumbnail_path:
                await self._set_thumbnail(video_info.thumbnail_path)
            
            # 设置地理位置
            if video_info.location:
                await self._set_location(video_info.location)
            
            # 设置同步到第三方平台
            await self._set_third_party_sync()
            
            # 设置定时发布
            if video_info.schedule_time:
                await self._set_schedule_time(video_info.schedule_time)
            
            # 发布视频
            return await self._publish_video()
            
        except Exception as e:
            logger.error(f"上传视频失败: {str(e)}")
            return False
            
    async def _wait_for_publish_page(self):
        """等待跳转到发布页面"""
        while True:
            try:
                # 尝试等待第一种URL
                await self.page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page", 
                    timeout=3000
                )
                logger.info("[+] 成功进入version_1发布页面!")
                break
            except:
                try:
                    # 尝试等待第二种URL
                    await self.page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                        timeout=3000
                    )
                    logger.info("[+] 成功进入version_2发布页面!")
                    break
                except:
                    logger.info("  [-] 等待进入视频发布页面...")
                    await asyncio.sleep(0.5)
                    
    async def _fill_video_info(self, video_info: DouyinVideoInfo):
        """填写视频信息"""
        logger.info("  [-] 正在填充标题和话题...")
        
        # 填写标题
        title_container = self.page.get_by_text('作品标题').locator("..").locator(
            "xpath=following-sibling::div[1]"
        ).locator("input")
        
        if await title_container.count():
            await title_container.fill(video_info.title[:30])
        else:
            # 备用方式
            titlecontainer = self.page.locator(".notranslate")
            await titlecontainer.click()
            await self.page.keyboard.press("Control+KeyA")
            await self.page.keyboard.press("Delete")
            await self.page.keyboard.type(video_info.title)
            await self.page.keyboard.press("Enter")
        
        # 添加话题标签
        css_selector = ".zone-container"
        for tag in video_info.tags:
            await self.page.type(css_selector, "#" + tag)
            await self.page.press(css_selector, "Space")
        
        logger.info(f"  [-] 总共添加{len(video_info.tags)}个话题")
        
    async def _wait_video_upload(self):
        """等待视频上传完成"""
        while True:
            try:
                # 查找重新上传按钮
                number = await self.page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if number > 0:
                    logger.success("  [-]视频上传完毕")
                    break
                else:
                    logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
                    
                    # 检查是否上传失败
                    if await self.page.locator('div.progress-div > div:has-text("上传失败")').count():
                        logger.error("  [-] 发现上传出错了... 准备重试")
                        # 重新上传
                        await self.page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(
                            str(self.current_video_path)
                        )
            except:
                logger.info("  [-] 正在上传视频中...")
                await asyncio.sleep(2)
                
    async def _set_thumbnail(self, thumbnail_path: Path):
        """设置视频封面"""
        try:
            await self.page.click('text="选择封面"')
            await self.page.wait_for_selector("div.semi-modal-content:visible")
            await self.page.click('text="设置竖封面"')
            await asyncio.sleep(2)
            
            # 上传封面图片
            await self.page.locator(
                "div[class^='semi-upload upload'] >> input.semi-upload-hidden-input"
            ).set_input_files(str(thumbnail_path))
            
            await asyncio.sleep(2)
            await self.page.locator("div[class^='extractFooter'] button:visible:has-text('完成')").click()
            logger.info("  [-] 封面设置完成")
        except Exception as e:
            logger.error(f"设置封面失败: {str(e)}")
            
    async def _set_location(self, location: str):
        """设置地理位置"""
        try:
            await self.page.locator('div.semi-select span:has-text("输入地理位置")').click()
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(2)
            await self.page.keyboard.type(location)
            await self.page.wait_for_selector('div[role="listbox"] [role="option"]', timeout=5000)
            await self.page.locator('div[role="listbox"] [role="option"]').first.click()
            logger.info(f"  [-] 已设置位置: {location}")
        except Exception as e:
            logger.error(f"设置位置失败: {str(e)}")
            
    async def _set_third_party_sync(self):
        """设置同步到第三方平台"""
        try:
            third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
            
            if await self.page.locator(third_part_element).count():
                # 检测是否已选中
                if 'semi-switch-checked' not in await self.page.eval_on_selector(
                    third_part_element, 'div => div.className'
                ):
                    await self.page.locator(third_part_element).locator('input.semi-switch-native-control').click()
                    logger.info("  [-] 已开启同步到头条/西瓜")
        except Exception as e:
            logger.debug(f"设置第三方同步失败: {str(e)}")
            
    async def _set_schedule_time(self, schedule_time: datetime):
        """设置定时发布"""
        try:
            # 选择定时发布
            label_element = self.page.locator("[class^='radio']:has-text('定时发布')")
            await label_element.click()
            await asyncio.sleep(1)
            
            # 输入时间
            publish_date_hour = schedule_time.strftime("%Y-%m-%d %H:%M")
            await self.page.locator('.semi-input[placeholder="日期和时间"]').click()
            await self.page.keyboard.press("Control+KeyA")
            await self.page.keyboard.type(publish_date_hour)
            await self.page.keyboard.press("Enter")
            
            logger.info(f"  [-] 已设置定时发布: {publish_date_hour}")
        except Exception as e:
            logger.error(f"设置定时发布失败: {str(e)}")
            
    async def _publish_video(self) -> bool:
        """发布视频"""
        try:
            while True:
                try:
                    publish_button = self.page.get_by_role('button', name="发布", exact=True)
                    if await publish_button.count():
                        await publish_button.click()
                    
                    # 等待跳转到作品管理页面
                    await self.page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/manage**",
                        timeout=3000
                    )
                    logger.success("  [-]视频发布成功")
                    
                    # 保存更新的cookies
                    await self._save_cookies(self.current_account)
                    logger.success('  [-]cookie更新完毕！')
                    
                    return True
                except:
                    logger.info("  [-] 视频正在发布中...")
                    await asyncio.sleep(0.5)
                    
        except Exception as e:
            logger.error(f"发布视频失败: {str(e)}")
            return False