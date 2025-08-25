"""
小红书自动上传器
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional, List

from playwright.async_api import async_playwright, Page, Browser
from ..models.platforms import XiaohongshuVideoInfo, XiaohongshuAccount
from ..utils.logger import logger


class XiaohongshuUploader:
    """小红书上传器"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        
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
        
        # 启动浏览器
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        
        # 创建上下文
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        self.page = await context.new_page()
        
        # 添加反检测脚本
        await self._add_stealth_script()
        
        logger.info("浏览器启动成功")
        
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
            
    async def login(self, account: XiaohongshuAccount) -> bool:
        """登录小红书"""
        try:
            logger.info(f"开始登录小红书账号: {account.name}")
            
            # 访问小红书创作者中心登录页面
            await self.page.goto("https://creator.xiaohongshu.com/login")
            await asyncio.sleep(3)
            
            # 尝试加载已保存的cookies
            if await self._load_cookies(account):
                logger.info("正在验证已保存的登录状态...")
                # 刷新页面以应用cookies
                await self.page.reload()
                await asyncio.sleep(2)
                
                # 验证登录状态
                if await self._verify_login_status():
                    self.is_logged_in = True
                    logger.info("使用已保存的登录状态")
                    return True
                else:
                    logger.info("已保存的登录状态已失效，需要重新登录")
                    
            # 检查是否需要扫码登录
            if await self._need_scan_login():
                logger.info("需要扫码登录，请使用小红书APP扫描二维码")
                logger.info("请在弹出的浏览器窗口中扫码登录")
                
                # 等待扫码登录完成
                success = await self._wait_for_login_success()
                if success:
                    await self._save_cookies(account)
                    self.is_logged_in = True
                    logger.info("登录成功")
                    return True
                else:
                    logger.error("登录失败或超时")
                    return False
            else:
                logger.error("无法确定登录状态，可能页面加载失败")
                return False
                
        except Exception as e:
            logger.error(f"登录过程出错: {str(e)}")
            return False
            
    async def _need_scan_login(self) -> bool:
        """检查是否需要扫码登录"""
        try:
            # 检查当前URL是否还在登录页面
            current_url = self.page.url
            logger.info(f"当前页面URL: {current_url}")
            
            # 如果已经在创作者中心页面，说明已登录
            if "creator.xiaohongshu.com" in current_url and "/publish" in current_url:
                return False
                
            # 检查是否有二维码元素或登录相关元素
            qr_selectors = [
                ".qrcode-img", ".login-qr", "[class*='qr']", 
                ".login-container", ".scan-login", "[class*='login']"
            ]
            
            for selector in qr_selectors:
                if await self.page.locator(selector).is_visible():
                    logger.info(f"发现登录元素: {selector}")
                    return True
                    
            # 等待页面加载完成，再次检查
            await asyncio.sleep(2)
            
            # 检查页面内容是否包含登录相关文本
            page_content = await self.page.content()
            login_keywords = ["登录", "扫码", "二维码", "login", "qr"]
            for keyword in login_keywords:
                if keyword in page_content:
                    logger.info(f"页面包含登录关键词: {keyword}")
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"检查登录状态失败: {str(e)}")
            return True
            
    async def _wait_for_login_success(self, timeout: int = 300) -> bool:
        """等待登录成功"""
        try:
            logger.info(f"等待登录完成，超时时间: {timeout}秒")
            # 等待页面跳转到创作者中心或者URL包含creator
            await self.page.wait_for_url("**/creator.xiaohongshu.com/**", timeout=timeout * 1000)
            await asyncio.sleep(2)
            logger.info("检测到页面跳转，登录成功")
            return True
        except Exception as e:
            logger.error(f"等待登录超时或失败: {str(e)}")
            return False
            
    async def _verify_login_status(self) -> bool:
        """验证登录状态"""
        try:
            # 访问创作者中心页面来验证登录状态
            await self.page.goto("https://creator.xiaohongshu.com/")
            await asyncio.sleep(3)
            
            current_url = self.page.url
            logger.info(f"小红书验证登录状态 - 当前URL: {current_url}")
            
            # 如果URL包含login说明需要登录，如果包含creator说明已登录
            if "login" in current_url:
                return False
            elif "creator.xiaohongshu.com" in current_url:
                return True
            else:
                # 检查页面内容是否有登录相关元素
                login_elements = await self.page.query_selector_all("[class*='login'], .qr")
                return len(login_elements) == 0
                
        except Exception as e:
            logger.error(f"验证小红书登录状态失败: {str(e)}")
            return False
            
    async def _save_cookies(self, account: XiaohongshuAccount):
        """保存cookies"""
        try:
            cookies = await self.page.context.cookies()
            
            # 确保cookies目录存在
            cookies_dir = Path("cookies")
            cookies_dir.mkdir(exist_ok=True)
            
            cookie_file = cookies_dir / f"xiaohongshu_{account.name}.json"
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
                
            account.cookie_file = cookie_file
            logger.info(f"Cookies已保存: {cookie_file}")
            
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            
    async def _load_cookies(self, account: XiaohongshuAccount) -> bool:
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
            
    async def upload_video(self, video_info: XiaohongshuVideoInfo) -> bool:
        """上传视频"""
        try:
            # 重新验证登录状态
            if not self.is_logged_in:
                logger.warning("登录状态未知，正在验证...")
                if not await self._verify_login_status():
                    logger.error("未登录或登录已失效，请重新登录")
                    return False
                else:
                    self.is_logged_in = True
                
            logger.info(f"开始上传视频: {video_info.video_path}")
            
            # 访问发布页面
            await self.page.goto("https://creator.xiaohongshu.com/publish/publish")
            await asyncio.sleep(5)
            
            logger.info(f"当前页面URL: {self.page.url}")
            
            # 检查是否成功进入发布页面
            if "publish" not in self.page.url:
                logger.error("未能进入发布页面，可能需要重新登录")
                return False
            
            # 上传视频文件
            if not await self._upload_video_file(video_info.video_path):
                return False
                
            # 等待视频处理完成
            if not await self._wait_video_processing():
                return False
                
            # 填写视频信息
            await self._fill_video_info(video_info)
            
            # 发布视频
            return await self._publish_video()
            
        except Exception as e:
            logger.error(f"上传视频失败: {str(e)}")
            return False
            
    async def _upload_video_file(self, video_path: Path) -> bool:
        """上传视频文件"""
        try:
            logger.info("正在寻找小红书文件上传区域...")
            
            # 等待页面完全加载
            await asyncio.sleep(3)
            
            # 小红书可能的文件上传选择器
            upload_selectors = [
                'input[type="file"]',
                'input[accept*="video"]',
                '.upload-btn input[type="file"]',
                '.upload-area input[type="file"]',
                '.file-upload input[type="file"]',
                '.video-upload input[type="file"]'
            ]
            
            file_input = None
            for selector in upload_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    for element in elements:
                        try:
                            # 检查是否可见或可用
                            is_visible = await element.is_visible()
                            is_enabled = await element.is_enabled()
                            if is_visible or is_enabled:
                                file_input = element
                                logger.info(f"找到文件上传输入框: {selector}")
                                break
                        except:
                            continue
                    if file_input:
                        break
            
            if not file_input:
                # 尝试查找并点击上传区域来触发文件选择
                upload_areas = [
                    '.upload-area',
                    '.upload-zone', 
                    '.drag-upload',
                    '.upload-btn',
                    '[class*="upload"]',
                    '.file-selector',
                    'button[class*="upload"]',
                    '.add-media',
                    '.media-upload'
                ]
                
                for selector in upload_areas:
                    try:
                        if await self.page.locator(selector).is_visible():
                            logger.info(f"点击上传区域: {selector}")
                            await self.page.click(selector)
                            await asyncio.sleep(2)
                            
                            # 再次查找文件输入框
                            file_input = await self.page.query_selector('input[type="file"]')
                            if file_input:
                                logger.info("点击后找到文件输入框")
                                break
                    except Exception as e:
                        logger.debug(f"尝试点击 {selector} 失败: {str(e)}")
                        continue
            
            if not file_input:
                logger.error("未找到文件上传输入框")
                # 截图保存现场以便调试
                await self.page.screenshot(path="debug_xiaohongshu_upload.png")
                logger.info("已保存页面截图: debug_xiaohongshu_upload.png")
                return False
                
            # 上传文件
            await file_input.set_input_files(str(video_path))
            logger.info(f"小红书视频文件 {video_path.name} 上传中...")
            
            return True
            
        except Exception as e:
            logger.error(f"上传视频文件失败: {str(e)}")
            return False
            
    async def _wait_video_processing(self, timeout: int = 300) -> bool:
        """等待视频处理完成"""
        try:
            # 等待视频预览出现
            preview_selectors = [
                ".video-preview",
                ".preview-container", 
                "[class*='preview']"
            ]
            
            for selector in preview_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=10000)
                    break
                except:
                    continue
            
            # 等待处理完成，检查进度条或loading状态
            loading_selectors = [
                ".loading",
                ".uploading",
                ".processing",
                "[class*='loading']",
                "[class*='progress']"
            ]
            
            for selector in loading_selectors:
                if await self.page.locator(selector).is_visible():
                    await self.page.wait_for_selector(selector, state="hidden", timeout=timeout * 1000)
                    
            logger.info("视频处理完成")
            return True
            
        except Exception as e:
            logger.error(f"等待视频处理超时: {str(e)}")
            return False
            
    async def _fill_video_info(self, video_info: XiaohongshuVideoInfo):
        """填写视频信息"""
        try:
            logger.info("开始填写小红书视频信息...")
            
            # 等待表单加载
            await asyncio.sleep(3)
            
            # 填写标题
            if video_info.title:
                title_selectors = [
                    ".title-input input",
                    ".title-input textarea", 
                    "input[placeholder*='标题']",
                    "textarea[placeholder*='标题']",
                    "input[placeholder*='title']",
                    ".note-title input",
                    ".post-title input"
                ]
                
                title_filled = False
                for selector in title_selectors:
                    try:
                        if await self.page.locator(selector).is_visible():
                            await self.page.fill(selector, video_info.title)
                            logger.info(f"已填写标题: {video_info.title}")
                            title_filled = True
                            break
                    except:
                        continue
                
                if not title_filled:
                    logger.warning("未找到标题输入框")
                
            # 填写描述/正文
            if video_info.description:
                desc_selectors = [
                    ".content-input textarea",
                    ".desc-input textarea",
                    ".editor-content",
                    "textarea[placeholder*='描述']",
                    "textarea[placeholder*='正文']",
                    "textarea[placeholder*='内容']",
                    ".note-content textarea",
                    ".post-content textarea",
                    ".text-editor textarea"
                ]
                
                desc_filled = False
                for selector in desc_selectors:
                    try:
                        if await self.page.locator(selector).is_visible():
                            await self.page.fill(selector, video_info.description)
                            logger.info(f"已填写描述: {video_info.description}")
                            desc_filled = True
                            break
                    except:
                        continue
                
                if not desc_filled:
                    logger.warning("未找到描述输入框")
                
            # 添加话题标签
            if video_info.topic_tags:
                await self._add_topic_tags(video_info.topic_tags)
                
            # 添加普通标签
            if video_info.tags:
                await self._add_tags(video_info.tags)
                
            # 设置位置
            if video_info.location:
                await self._set_location(video_info.location)
                
            # 设置可见性
            await self._set_visibility(video_info.visible_type)
            
            logger.info("小红书视频信息填写完成")
                
        except Exception as e:
            logger.error(f"填写视频信息失败: {str(e)}")
            
    async def _add_topic_tags(self, topic_tags: List[str]):
        """添加话题标签"""
        try:
            for tag in topic_tags:
                # 在描述框中添加话题标签格式
                topic_text = f"#{tag}#"
                
                # 找到描述输入框
                desc_selectors = [
                    ".content-input textarea",
                    ".desc-input textarea",
                    ".editor-content"
                ]
                
                for selector in desc_selectors:
                    if await self.page.locator(selector).is_visible():
                        # 获取当前内容
                        current_text = await self.page.input_value(selector)
                        # 添加话题标签
                        new_text = f"{current_text} {topic_text}"
                        await self.page.fill(selector, new_text)
                        break
                        
                await asyncio.sleep(0.5)
                
            logger.info(f"已添加话题标签: {topic_tags}")
            
        except Exception as e:
            logger.error(f"添加话题标签失败: {str(e)}")
            
    async def _add_tags(self, tags: List[str]):
        """添加普通标签"""
        try:
            # 查找标签输入区域
            tag_selectors = [
                ".tag-input",
                ".tags-input",
                "[placeholder*='标签']"
            ]
            
            for tag in tags:
                for selector in tag_selectors:
                    if await self.page.locator(selector).is_visible():
                        await self.page.fill(selector, tag)
                        await self.page.press(selector, "Enter")
                        await asyncio.sleep(0.5)
                        break
                        
            logger.info(f"已添加标签: {tags}")
            
        except Exception as e:
            logger.error(f"添加标签失败: {str(e)}")
            
    async def _set_location(self, location: str):
        """设置地理位置"""
        try:
            # 查找位置设置按钮
            location_selectors = [
                ".location-btn",
                ".add-location",
                "[class*='location']"
            ]
            
            for selector in location_selectors:
                if await self.page.locator(selector).is_visible():
                    await self.page.click(selector)
                    await asyncio.sleep(1)
                    
                    # 搜索位置
                    search_input = ".location-search input, .search-input input"
                    if await self.page.locator(search_input).is_visible():
                        await self.page.fill(search_input, location)
                        await asyncio.sleep(2)
                        
                        # 选择第一个搜索结果
                        first_result = ".location-list .location-item:first-child, .search-result:first-child"
                        if await self.page.locator(first_result).is_visible():
                            await self.page.click(first_result)
                            logger.info(f"已设置位置: {location}")
                            return
                            
        except Exception as e:
            logger.error(f"设置位置失败: {str(e)}")
            
    async def _set_visibility(self, visible_type: str):
        """设置可见性"""
        try:
            # 查找隐私设置
            privacy_selectors = [
                ".privacy-setting",
                ".visibility-setting",
                "[class*='privacy']",
                "[class*='visibility']"
            ]
            
            for selector in privacy_selectors:
                if await self.page.locator(selector).is_visible():
                    await self.page.click(selector)
                    await asyncio.sleep(1)
                    
                    # 根据可见性类型选择对应选项
                    if visible_type == "public":
                        option_selector = "[data-value='public'], .public-option"
                    elif visible_type == "friends":
                        option_selector = "[data-value='friends'], .friends-option"
                    else:  # private
                        option_selector = "[data-value='private'], .private-option"
                        
                    if await self.page.locator(option_selector).is_visible():
                        await self.page.click(option_selector)
                        logger.info(f"已设置可见性: {visible_type}")
                        return
                        
        except Exception as e:
            logger.error(f"设置可见性失败: {str(e)}")
            
    async def _publish_video(self) -> bool:
        """发布视频"""
        try:
            # 查找发布按钮
            publish_selectors = [
                ".publish-btn",
                ".submit-btn",
                "[class*='publish']",
                "[class*='submit']"
            ]
            
            for selector in publish_selectors:
                if await self.page.locator(selector).is_visible():
                    await self.page.click(selector)
                    break
            
            # 等待发布完成
            await asyncio.sleep(3)
            
            # 检查是否发布成功
            if await self._check_publish_success():
                logger.info("视频发布成功")
                return True
            else:
                logger.error("视频发布失败")
                return False
                
        except Exception as e:
            logger.error(f"发布视频失败: {str(e)}")
            return False
            
    async def _check_publish_success(self) -> bool:
        """检查发布是否成功"""
        try:
            # 查找成功提示
            success_selectors = [
                ".success-tip",
                ".success-message", 
                "[class*='success']",
                ".publish-success"
            ]
            
            for selector in success_selectors:
                if await self.page.locator(selector).is_visible():
                    return True
                    
            # 检查是否跳转到作品管理页面
            await asyncio.sleep(2)
            current_url = self.page.url
            return "manage" in current_url or "content" in current_url
            
        except:
            return False