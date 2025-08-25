"""
微信视频号自动上传器
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional, List

from playwright.async_api import async_playwright, Page, Browser
from ..models.platforms import WechatChannelVideoInfo, WechatChannelAccount
from ..utils.logger import logger


class WechatChannelUploader:
    """微信视频号上传器"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.current_account: Optional[WechatChannelAccount] = None
        self.current_video_path: Optional[Path] = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_browser()
        
    async def start_browser(self):
        """启动浏览器 - 使用系统Chrome避免H264编码问题"""
        playwright = await async_playwright().start()
        
        # 检测系统Chrome路径
        chrome_path = self._get_chrome_path()
        
        # 启动浏览器 - 使用系统Chrome
        launch_options = {
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        }
        
        if chrome_path and not self.headless:
            # 非无头模式下使用系统Chrome
            launch_options['executable_path'] = chrome_path
            logger.info(f"使用系统Chrome: {chrome_path}")
        
        self.browser = await playwright.chromium.launch(**launch_options)
        
        # 创建上下文
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
                "/usr/bin/chromium-browser",
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
            
    async def login(self, account: WechatChannelAccount) -> bool:
        """登录微信视频号"""
        try:
            logger.info(f"开始登录微信视频号账号: {account.name}")
            
            # 保存当前账号
            self.current_account = account
            
            # 先尝试加载已保存的cookies
            if await self._load_cookies(account):
                logger.info("正在验证已保存的登录状态...")
                
            # 访问微信视频号创作者中心
            await self.page.goto("https://channels.weixin.qq.com/platform/login")
            await asyncio.sleep(3)
            
            # 验证登录状态
            if await self._verify_login_status():
                self.is_logged_in = True
                logger.info("使用已保存的登录状态")
                return True
            
            # 检查是否需要扫码登录
            if await self._need_scan_login():
                logger.info("需要扫码登录，请使用微信扫描二维码")
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
                logger.error("无法确定登录状态")
                return False
                
        except Exception as e:
            logger.error(f"登录过程出错: {str(e)}")
            return False
            
    async def _need_scan_login(self) -> bool:
        """检查是否需要扫码登录"""
        try:
            # 检查当前URL
            current_url = self.page.url
            logger.info(f"当前页面URL: {current_url}")
            
            # 如果已经在平台页面，说明已登录
            if "channels.weixin.qq.com/platform" in current_url and "login" not in current_url:
                return False
                
            # 检查是否有二维码元素或登录相关元素
            qr_selectors = [
                ".login-qrcode", ".qrcode", "[class*='qr']",
                ".login-container", "[class*='login']", ".scan-login"
            ]
            
            for selector in qr_selectors:
                if await self.page.locator(selector).is_visible():
                    logger.info(f"发现登录元素: {selector}")
                    return True
                    
            # 等待页面加载完成
            await asyncio.sleep(2)
            
            # 检查页面内容
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
            # 等待页面跳转到创作者中心
            await self.page.wait_for_url("**/platform/**", timeout=timeout * 1000)
            await asyncio.sleep(2)
            return True
        except:
            return False
            
    async def _verify_login_status(self) -> bool:
        """验证登录状态"""
        try:
            # 访问一个需要登录的页面来验证
            await self.page.goto("https://channels.weixin.qq.com/platform/post/create")
            await asyncio.sleep(3)
            
            current_url = self.page.url
            logger.info(f"验证登录状态 - 当前URL: {current_url}")
            
            # 如果包含login说明需要登录，如果包含platform说明已登录
            if "login" in current_url:
                return False
            elif "platform" in current_url:
                return True
            else:
                # 检查页面内容是否有登录相关元素
                login_elements = await self.page.query_selector_all("[class*='login'], .qr")
                return len(login_elements) == 0
                
        except Exception as e:
            logger.error(f"验证登录状态失败: {str(e)}")
            return False
            
    async def _save_cookies(self, account: WechatChannelAccount):
        """保存cookies"""
        try:
            cookies = await self.page.context.cookies()
            
            # 确保cookies目录存在
            cookies_dir = Path("cookies")
            cookies_dir.mkdir(exist_ok=True)
            
            cookie_file = cookies_dir / f"wechat_channel_{account.name}.json"
            
            with open(cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
                
            account.cookie_file = cookie_file
            logger.info(f"Cookies已保存: {cookie_file}")
            
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
            
    async def _load_cookies(self, account: WechatChannelAccount) -> bool:
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
            
    async def upload_video(self, video_info: WechatChannelVideoInfo) -> bool:
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
                
            logger.info(f"[+]正在上传-------{video_info.title}.mp4")
            
            # 保存当前视频路径供重试使用
            self.current_video_path = video_info.video_path
            
            # 访问发布页面
            await self.page.goto("https://channels.weixin.qq.com/platform/post/create")
            # 等待页面跳转完成
            await self.page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")
            
            # 上传视频文件
            if not await self._upload_video_file(video_info.video_path):
                return False
            
            # 填写标题和话题
            await self._fill_video_info(video_info)
            
            # 添加合集（如果有）
            await self._add_collection()
            
            # 原创选择
            await self._set_original_declaration()
            
            # 检测上传状态
            if not await self._wait_video_processing():
                return False
            
            # 保存更新的cookies
            await self._save_cookies(self.current_account)
            logger.success('  [-]cookie更新完毕！')
            
            # 发布视频
            return await self._publish_video()
            
        except Exception as e:
            logger.error(f"上传视频失败: {str(e)}")
            return False
            
    async def _upload_video_file(self, video_path: Path) -> bool:
        """上传视频文件 - 基于social-auto-upload的实现"""
        try:
            logger.info(f"[+]正在上传视频: {video_path.name}")
            
            # 等待页面完全加载
            await asyncio.sleep(2)
            
            # 等待文件输入框出现（不需要可见）
            await self.page.wait_for_selector('input[type="file"]', state='attached', timeout=10000)
            
            # 直接定位文件输入框
            file_input = self.page.locator('input[type="file"]')
            
            # 确保元素存在
            count = await file_input.count()
            logger.info(f"  [-]找到 {count} 个文件输入框")
            
            if count == 0:
                logger.error("未找到文件上传输入框")
                return False
            
            # 直接设置文件（即使元素是隐藏的）
            await file_input.set_input_files(str(video_path))
            
            logger.info("  [-]视频文件已设置，等待上传...")
            
            # 等待一小段时间确保文件开始上传
            await asyncio.sleep(2)
            
            return True
                
        except Exception as e:
            logger.error(f"上传视频文件失败: {str(e)}")
            return False
    
    async def _try_set_file_input(self, video_path: Path) -> bool:
        """尝试设置文件输入框"""
        try:
            # 查找文件输入框的多种可能选择器
            file_input_selectors = [
                'input[type="file"][accept*="video"]',
                'input[type="file"][accept*="mp4"]', 
                'input[type="file"][accept*="media"]',
                '.upload input[type="file"]',
                '.upload-wrap input[type="file"]',
                '.post-upload-wrap input[type="file"]',
                'input[type="file"]'  # 最后的通用选择器
            ]
            
            for selector in file_input_selectors:
                try:
                    locator = self.page.locator(selector)
                    count = await locator.count()
                    
                    if count > 0:
                        logger.info(f"找到 {count} 个文件输入框: {selector}")
                        
                        # 尝试所有匹配的文件输入框
                        for i in range(count):
                            try:
                                element_locator = locator.nth(i)
                                
                                # 检查元素是否可用（可见或启用）
                                is_visible = await element_locator.is_visible()
                                is_enabled = await element_locator.is_enabled()
                                
                                logger.info(f"文件输入框 {i+1}: visible={is_visible}, enabled={is_enabled}")
                                
                                if is_enabled:  # 只要启用即可，不一定要可见
                                    logger.info(f"使用文件输入框: {selector} (第{i+1}个)")
                                    await element_locator.set_input_files(str(video_path))
                                    
                                    # 等待一段时间让文件处理
                                    await asyncio.sleep(1)
                                    
                                    # 多种方式验证文件是否成功设置
                                    try:
                                        # 方式1: 检查files属性
                                        files_count = await element_locator.evaluate("el => el.files ? el.files.length : 0")
                                        logger.debug(f"文件输入框files.length: {files_count}")
                                        
                                        # 方式2: 检查value属性
                                        file_value = await element_locator.evaluate("el => el.value")
                                        logger.debug(f"文件输入框value: {file_value}")
                                        
                                        # 方式3: 检查页面是否有上传成功的迹象
                                        upload_success_indicators = await self._check_upload_success_indicators()
                                        logger.debug(f"上传成功指示器: {upload_success_indicators}")
                                        
                                        # 如果有任何成功迹象，认为上传成功
                                        if files_count > 0 or file_value or upload_success_indicators:
                                            logger.info(f"文件上传成功检测 - files: {files_count}, value: {bool(file_value)}, indicators: {upload_success_indicators}")
                                            return True
                                        else:
                                            logger.debug(f"文件输入框 {i+1} 设置文件后没有检测到成功迹象")
                                            
                                    except Exception as verify_e:
                                        logger.debug(f"验证文件设置时出错: {str(verify_e)}")
                                        # 即使验证出错，也尝试继续，可能文件已经设置成功
                                        continue
                                        
                            except Exception as inner_e:
                                logger.debug(f"设置文件输入框 {i+1} 失败: {str(inner_e)}")
                                continue
                                
                except Exception as e:
                    logger.debug(f"处理选择器 {selector} 失败: {str(e)}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"尝试设置文件输入框失败: {str(e)}")
            return False
    
    async def _debug_upload_elements(self):
        """调试：输出页面中的上传相关元素"""
        try:
            # 查找所有包含upload的元素
            upload_elements = await self.page.query_selector_all('[class*="upload"], [id*="upload"], [data-testid*="upload"]')
            logger.info(f"找到 {len(upload_elements)} 个包含upload的元素")
            
            # 查找所有文件输入框
            file_inputs = await self.page.query_selector_all('input[type="file"]')
            logger.info(f"找到 {len(file_inputs)} 个文件输入框")
            
            # 查找所有按钮
            buttons = await self.page.query_selector_all('button')
            logger.info(f"找到 {len(buttons)} 个按钮")
            
            # 输出页面源码的关键部分
            page_content = await self.page.content()
            with open("debug_wechat_page_full.html", "w", encoding="utf-8") as f:
                f.write(page_content)
            logger.info("已保存完整页面内容: debug_wechat_page_full.html")
            
        except Exception as e:
            logger.error(f"调试输出失败: {str(e)}")
            
    async def _check_upload_success_indicators(self) -> bool:
        """检查页面是否有上传成功的指示器"""
        try:
            # 检查页面中是否出现了上传成功的迹象
            success_indicators = [
                # 可能的成功元素
                '.upload-success',
                '.upload-complete',
                '.file-uploaded',
                '.video-preview',
                '.media-preview',
                '.upload-progress[style*="100%"]',
                # 可能的错误消息（如果没有错误消息，说明可能成功了）
                '.error-message',
                '.upload-error',
                # 检查是否出现了视频处理相关元素
                '.processing',
                '.uploading',
                '.video-processing',
                # 检查是否页面结构发生了变化（出现了编辑区域）
                '.video-info-form',
                '.post-edit-form',
                '.content-editor'
            ]
            
            success_count = 0
            error_count = 0
            
            for selector in success_indicators:
                try:
                    count = await self.page.locator(selector).count()
                    if count > 0:
                        if 'error' in selector.lower():
                            error_count += count
                            logger.debug(f"发现错误指示器: {selector} ({count}个)")
                        else:
                            success_count += count
                            logger.debug(f"发现成功指示器: {selector} ({count}个)")
                except:
                    continue
            
            # 检查页面URL是否发生了变化（可能跳转到了编辑页面）
            current_url = self.page.url
            logger.debug(f"当前URL: {current_url}")
            
            # 如果有成功指示器且没有错误指示器，认为上传成功
            has_success_indicators = success_count > 0 and error_count == 0
            logger.debug(f"上传指示器统计 - 成功: {success_count}, 错误: {error_count}")
            
            return has_success_indicators
            
        except Exception as e:
            logger.error(f"检查上传成功指示器失败: {str(e)}")
            return False
            
    async def _wait_video_processing(self, timeout: int = 60) -> bool:
        """等待视频处理完成 - 基于social-auto-upload实现"""
        try:
            logger.info("  [-]检测视频上传状态...")
            
            while True:
                try:
                    # 检查发表按钮是否可用（表示上传完成）
                    publish_button = self.page.get_by_role("button", name="发表")
                    button_class = await publish_button.get_attribute('class')
                    
                    if button_class and "weui-desktop-btn_disabled" not in button_class:
                        logger.info("  [-]视频上传完毕")
                        break
                    else:
                        logger.info("  [-]正在上传视频中...")
                        await asyncio.sleep(2)
                        
                        # 检查是否有错误并处理
                        if await self.page.locator('div.status-msg.error').count():
                            if await self.page.locator('div.media-status-content div.tag-inner:has-text("删除")').count():
                                logger.error("  [-]发现上传错误，准备重试...")
                                await self.page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
                                await self.page.get_by_role('button', name="删除", exact=True).click()
                                # 重新上传
                                file_input = self.page.locator('input[type="file"]')
                                if hasattr(self, 'current_video_path'):
                                    await file_input.set_input_files(str(self.current_video_path))
                                    logger.info("  [-]重新上传视频文件...")
                            else:
                                logger.error("  [-]发现上传错误")
                                return False
                            
                except Exception:
                    logger.info("  [-]正在上传视频中...")
                    await asyncio.sleep(2)
                    
            return True
            
        except Exception as e:
            logger.error(f"等待视频处理时出错: {str(e)}")
            return True
            
    async def _fill_video_info(self, video_info: WechatChannelVideoInfo):
        """填写视频信息 - 基于social-auto-upload实现"""
        try:
            logger.info("  [-]填写视频标题和标签...")
            
            # 点击输入区域
            await self.page.locator("div.input-editor").click()
            
            # 输入标题
            await self.page.keyboard.type(video_info.title)
            await self.page.keyboard.press("Enter")
            
            # 添加标签
            if video_info.tags:
                for tag in video_info.tags:
                    await self.page.keyboard.type(f"#{tag}")
                    await self.page.keyboard.press("Space")
                logger.info(f"  [-]成功添加标签: {len(video_info.tags)}个")
                
            # 设置原创（如果需要）
            if video_info.original_statement:
                await self._set_original_declaration()
                
            logger.info("  [-]视频信息填写完成")
                
        except Exception as e:
            logger.error(f"填写视频信息失败: {str(e)}")
            
    async def _add_tags(self, tags: List[str]):
        """添加话题标签"""
        try:
            for tag in tags:
                # 点击话题按钮
                topic_btn = ".topic-btn"
                await self.page.click(topic_btn)
                await asyncio.sleep(1)
                
                # 输入话题
                topic_input = ".topic-input input"
                await self.page.fill(topic_input, tag)
                await self.page.press(topic_input, "Enter")
                await asyncio.sleep(1)
                
            logger.info(f"已添加话题标签: {tags}")
            
        except Exception as e:
            logger.error(f"添加话题标签失败: {str(e)}")
            
    async def _set_location(self, location: str):
        """设置地理位置"""
        try:
            # 点击位置按钮
            location_btn = ".location-btn"
            await self.page.click(location_btn)
            await asyncio.sleep(1)
            
            # 搜索位置
            location_input = ".location-search input"
            await self.page.fill(location_input, location)
            await asyncio.sleep(2)
            
            # 选择第一个搜索结果
            first_result = ".location-list .location-item:first-child"
            if await self.page.locator(first_result).is_visible():
                await self.page.click(first_result)
                logger.info(f"已设置位置: {location}")
                
        except Exception as e:
            logger.error(f"设置位置失败: {str(e)}")
            
    async def _set_original_declaration(self):
        """设置原创声明 - 基于social-auto-upload实现"""
        try:
            # 查找原创选项
            if await self.page.get_by_label("视频为原创").count():
                await self.page.get_by_label("视频为原创").check()
                logger.info("  [-]已勾选原创")
                
            # 检查是否需要同意条款
            label_locator = await self.page.locator('label:has-text("我已阅读并同意 《视频号原创声明使用条款》")').is_visible()
            if label_locator:
                await self.page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
                await self.page.get_by_role("button", name="声明原创").click()
                logger.info("  [-]已声明原创")
                
            # 2023年11月20日 wechat更新: 新的原创声明界面
            if await self.page.locator('div.label span:has-text("声明原创")').count():
                # 检查是否可以勾选原创
                if not await self.page.locator('div.declare-original-checkbox input.ant-checkbox-input').is_disabled():
                    await self.page.locator('div.declare-original-checkbox input.ant-checkbox-input').click()
                    if not await self.page.locator('div.declare-original-dialog label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible').count():
                        await self.page.locator('div.declare-original-dialog input.ant-checkbox-input:visible').click()
                if await self.page.locator('button:has-text("声明原创"):visible').count():
                    await self.page.locator('button:has-text("声明原创"):visible').click()
                    logger.info("  [-]已声明原创（新版界面）")
                
        except Exception as e:
            logger.debug(f"设置原创声明失败（可能不需要）: {str(e)}")
            
    async def _publish_video(self) -> bool:
        """发布视频 - 基于social-auto-upload实现"""
        try:
            logger.info("  [-]准备发布视频...")
            
            while True:
                try:
                    # 查找发表按钮
                    publish_button = self.page.locator('div.form-btns button:has-text("发表")')
                    if await publish_button.count():
                        await publish_button.click()
                        logger.info("  [-]已点击发表按钮")
                    
                    # 等待页面跳转到发布成功页面
                    await self.page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=5000)
                    logger.success("  [-]视频发布成功")
                    break
                    
                except Exception as e:
                    # 检查当前URL是否已经跳转
                    current_url = self.page.url
                    if "https://channels.weixin.qq.com/platform/post/list" in current_url:
                        logger.success("  [-]视频发布成功")
                        break
                    else:
                        logger.info("  [-]视频正在发布中...")
                        await asyncio.sleep(0.5)
            
            return True
                
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
                "[class*='success']"
            ]
            
            for selector in success_selectors:
                if await self.page.locator(selector).is_visible():
                    return True
                    
            # 检查是否跳转到作品管理页面
            await asyncio.sleep(2)
            current_url = self.page.url
            return "manage" in current_url or "list" in current_url
            
        except:
            return False
    
    async def _add_collection(self):
        """添加到合集"""
        try:
            collection_elements = self.page.get_by_text("添加到合集").locator("xpath=following-sibling::div").locator(
                '.option-list-wrap > div')
            if await collection_elements.count() > 1:
                await self.page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
                await collection_elements.first.click()
                logger.info("  [-]已添加到合集")
        except Exception as e:
            logger.debug(f"添加到合集失败（可能不需要）: {str(e)}")