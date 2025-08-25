# -*- coding: utf-8 -*-

"""
抖音上传器模块
基于Playwright实现的抖音视频上传功能
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from playwright.async_api import Playwright, async_playwright, Page

from ..models.config import Config
from ..utils.logger import get_logger


class DouyinUploader:
    """抖音上传器类"""

    def __init__(self, account_name: str, cookie_file: str, config: Config):
        self.account_name = account_name
        self.cookie_file = cookie_file
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        self.date_format = '%Y年%m月%d日 %H:%M'

    async def check_cookie(self) -> bool:
        """检查Cookie是否有效"""
        if not os.path.exists(self.cookie_file):
            self.logger.warning(f"Cookie文件不存在: {self.cookie_file}")
            return False

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(storage_state=self.cookie_file)
                await self._set_init_script(context)

                page = await context.new_page()
                await page.goto("https://creator.douyin.com/creator-micro/content/upload")

                try:
                    await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
                except:
                    self.logger.warning("等待5秒 cookie 失效")
                    await context.close()
                    await browser.close()
                    return False

                # 检查是否需要登录
                if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
                    self.logger.warning("cookie 失效，需要重新登录")
                    await context.close()
                    await browser.close()
                    return False
                else:
                    self.logger.info("cookie 有效")
                    await context.close()
                    await browser.close()
                    return True

        except Exception as e:
            self.logger.error(f"检查Cookie时发生错误: {str(e)}")
            return False

    async def login(self) -> bool:
        """登录并生成Cookie"""
        try:
            # 确保Cookie目录存在
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=False)
                context = await browser.new_context()
                await self._set_init_script(context)

                page = await context.new_page()
                await page.goto("https://creator.douyin.com/")

                self.logger.info("请在浏览器中完成登录，登录完成后点击调试器的继续按钮")
                await page.pause()

                # 保存Cookie
                await context.storage_state(path=self.cookie_file)
                await browser.close()

                self.logger.info(f"Cookie已保存到: {self.cookie_file}")
                return True

        except Exception as e:
            self.logger.error(f"登录过程中发生错误: {str(e)}")
            return False

    async def upload_video(self,
                           video_path: str,
                           title: str,
                           tags: List[str],
                           thumbnail_path: str = None,
                           publish_date: datetime = None,
                           location: str = "杭州市") -> bool:
        """
        上传视频到抖音

        Args:
            video_path: 视频文件路径
            title: 视频标题
            tags: 话题标签列表
            thumbnail_path: 缩略图路径
            publish_date: 发布时间(None表示立即发布)
            location: 地理位置

        Returns:
            bool: 上传是否成功
        """
        try:
            async with async_playwright() as playwright:
                return await self._upload_video_impl(
                    playwright, video_path, title, tags,
                    thumbnail_path, publish_date, location
                )
        except Exception as e:
            self.logger.error(f"上传视频时发生错误: {str(e)}")
            return False

    async def _upload_video_impl(self,
                                 playwright: Playwright,
                                 video_path: str,
                                 title: str,
                                 tags: List[str],
                                 thumbnail_path: str = None,
                                 publish_date: datetime = None,
                                 location: str = "北京市") -> bool:
        """上传视频的具体实现"""

        # 启动浏览器
        if self.config.chrome_path:
            browser = await playwright.chromium.launch(
                headless=False,
                executable_path=self.config.chrome_path
            )
        else:
            browser = await playwright.chromium.launch(headless=False)

        # 创建上下文并设置权限
        context = await browser.new_context(
            storage_state=self.cookie_file,
            permissions=['geolocation'],  # 预先允许地理位置权限
            geolocation={'latitude': 39.9042, 'longitude': 116.4074}  # 默认北京坐标
        )
        await self._set_init_script(context)

        page = await context.new_page()

        # 设置页面权限处理
        await self._setup_page_permissions(page)

        try:
            # 访问上传页面
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            self.logger.info(f'[+]正在上传-------{title}.mp4')

            # 等待页面加载
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload")

            # 上传视频文件
            await page.locator("div[class^='container'] input").set_input_files(video_path)

            # 等待进入发布页面
            await self._wait_for_publish_page(page)

            # 填充标题和话题
            await self._fill_title_and_tags(page, title, tags)

            # 等待视频上传完成
            await self._wait_for_upload_complete(page, video_path)

            # 设置缩略图
            if thumbnail_path:
                await self._set_thumbnail(page, thumbnail_path)

            # 设置地理位置
            await self._set_location(page, location)

            # 设置第三方平台同步
            await self._set_third_party_sync(page)

            # 设置定时发布
            if publish_date:
                await self._set_schedule_time(page, publish_date)

            # 发布视频
            await self._publish_video(page)

            # 保存Cookie
            await context.storage_state(path=self.cookie_file)
            self.logger.info('Cookie已更新')

            await asyncio.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"上传过程中发生错误: {str(e)}")
            await page.screenshot(path=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            return False

        finally:
            await context.close()
            await browser.close()

    async def _wait_for_publish_page(self, page: Page):
        """等待进入发布页面"""
        self.logger.info("等待进入发布页面...")
        while True:
            try:
                # 尝试等待第一个版本的URL
                await page.wait_for_url(
                    "https://creator.douyin.com/creator-micro/content/publish?enter_from=publish_page",
                    timeout=3000
                )
                self.logger.info("成功进入version_1发布页面!")
                break
            except Exception:
                try:
                    # 尝试等待第二个版本的URL
                    await page.wait_for_url(
                        "https://creator.douyin.com/creator-micro/content/post/video?enter_from=publish_page",
                        timeout=3000
                    )
                    self.logger.info("成功进入version_2发布页面!")
                    break
                except:
                    self.logger.info("超时未进入视频发布页面，重新尝试...")
                    await asyncio.sleep(0.5)

    async def _fill_title_and_tags(self, page: Page, title: str, tags: List[str]):
        """填充标题和话题"""
        await asyncio.sleep(1)
        self.logger.info("正在填充标题和话题...")

        # 填充标题
        title_container = page.get_by_text('作品标题').locator("..").locator("xpath=following-sibling::div[1]").locator(
            "input"
            )
        if await title_container.count():
            await title_container.fill(title[:30])
        else:
            title_container = page.locator(".notranslate")
            await title_container.click()
            await page.keyboard.press("Backspace")
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.press("Delete")
            await page.keyboard.type(title)
            await page.keyboard.press("Enter")

        # 填充话题标签
        css_selector = ".zone-container"
        for tag in tags:
            await page.type(css_selector, "#" + tag)
            await page.press(css_selector, "Space")

        self.logger.info(f'总共添加{len(tags)}个话题')

    async def _wait_for_upload_complete(self, page: Page, video_path: str):
        """等待视频上传完成"""
        self.logger.info("等待视频上传完成...")
        while True:
            try:
                # 检查是否有重新上传按钮
                number = await page.locator('[class^="long-card"] div:has-text("重新上传")').count()
                if number > 0:
                    self.logger.info("视频上传完毕")
                    break
                else:
                    self.logger.info("正在上传视频中...")
                    await asyncio.sleep(2)

                    # 检查是否上传失败
                    if await page.locator('div.progress-div > div:has-text("上传失败")').count():
                        self.logger.error("发现上传出错了... 准备重试")
                        await self._handle_upload_error(page, video_path)
            except:
                self.logger.info("正在上传视频中...")
                await asyncio.sleep(2)

    async def _handle_upload_error(self, page: Page, video_path: str):
        """处理上传错误"""
        self.logger.info('视频出错了，重新上传中')
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(video_path)

    async def _set_thumbnail(self, page: Page, thumbnail_path: str):
        """设置视频缩略图"""
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            self.logger.info("缩略图路径无效，跳过缩略图设置")
            return

        self.logger.info(f"开始设置缩略图: {thumbnail_path}")

        try:
            # 尝试点击选择封面按钮 - 多种定位方式
            cover_button_clicked = False
            cover_selectors = [
                'text="选择封面"',
                'button:has-text("选择封面")',
                '[data-testid="cover-select"]',
                '.cover-select-btn',
                'button[class*="cover"]'
            ]

            for selector in cover_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    await page.click(selector)
                    self.logger.info(f"成功点击选择封面按钮: {selector}")
                    cover_button_clicked = True
                    break
                except Exception as e:
                    self.logger.debug(f"尝试选择器 {selector} 失败: {str(e)}")
                    continue

            if not cover_button_clicked:
                self.logger.warning("未找到选择封面按钮，跳过缩略图设置")
                return

            # 等待弹窗出现
            try:
                await page.wait_for_selector("div.semi-modal-content:visible", timeout=5000)
                self.logger.info("封面设置弹窗已打开")
            except:
                self.logger.warning("未检测到封面设置弹窗，继续尝试")

            await asyncio.sleep(1)

            # 尝试点击设置竖封面 - 多种方式
            vertical_cover_clicked = False
            vertical_selectors = [
                'text="设置竖封面"',
                'button:has-text("设置竖封面")',
                'text="竖封面"',
                'button:has-text("竖封面")',
                '[data-testid="vertical-cover"]',
                '.vertical-cover-btn',
                'button[class*="vertical"]'
            ]

            for selector in vertical_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    await page.click(selector)
                    self.logger.info(f"成功点击设置竖封面: {selector}")
                    vertical_cover_clicked = True
                    break
                except Exception as e:
                    self.logger.debug(f"尝试竖封面选择器 {selector} 失败: {str(e)}")
                    continue

            if not vertical_cover_clicked:
                self.logger.warning("未找到设置竖封面按钮，尝试直接上传")

            await asyncio.sleep(2)

            # 尝试上传缩略图 - 多种文件上传方式
            upload_success = False
            upload_selectors = [
                "div[class^='semi-upload upload'] >> input.semi-upload-hidden-input",
                "input[type='file'][accept*='image']",
                "input.semi-upload-hidden-input",
                "input[type='file']",
                ".upload-input input",
                "[data-testid='file-upload'] input"
            ]

            for selector in upload_selectors:
                try:
                    upload_input = page.locator(selector)
                    if await upload_input.count() > 0:
                        await upload_input.set_input_files(thumbnail_path)
                        self.logger.info(f"成功上传缩略图文件: {selector}")
                        upload_success = True
                        break
                except Exception as e:
                    self.logger.debug(f"尝试上传选择器 {selector} 失败: {str(e)}")
                    continue

            if not upload_success:
                self.logger.error("无法找到文件上传输入框")
                return

            # 等待上传完成
            await asyncio.sleep(3)

            # 尝试点击完成按钮 - 多种方式
            complete_clicked = False
            complete_selectors = [
                "div[class^='extractFooter'] button:visible:has-text('完成')",
                "button:has-text('完成')",
                "button:has-text('确定')",
                "button:has-text('保存')",
                "[data-testid='confirm-btn']",
                ".confirm-btn",
                ".save-btn"
            ]

            for selector in complete_selectors:
                try:
                    complete_btn = page.locator(selector)
                    if await complete_btn.count() > 0:
                        await complete_btn.click()
                        self.logger.info(f"成功点击完成按钮: {selector}")
                        complete_clicked = True
                        break
                except Exception as e:
                    self.logger.debug(f"尝试完成按钮选择器 {selector} 失败: {str(e)}")
                    continue

            if not complete_clicked:
                self.logger.warning("未找到完成按钮，尝试按ESC键关闭弹窗")
                await page.keyboard.press("Escape")

            await asyncio.sleep(1)
            self.logger.info("缩略图设置流程完成")

        except Exception as e:
            self.logger.error(f"设置缩略图时发生错误: {str(e)}")
            self.logger.info("缩略图设置失败，但不影响视频上传，继续后续流程")

            # 尝试关闭可能打开的弹窗
            try:
                await page.keyboard.press("Escape")
                await asyncio.sleep(1)
            except:
                pass

    async def _set_location(self, page: Page, location: str):
        """设置地理位置"""
        if not location:
            self.logger.info("未指定地理位置，跳过设置")
            return

        self.logger.info(f"开始设置地理位置: {location}")

        try:
            # 处理可能出现的地理位置权限弹窗
            await self._handle_geolocation_permission(page)

            # 多种地理位置输入框定位器
            location_input_clicked = False
            location_selectors = [
                'div.semi-select span:has-text("输入地理位置")',
                'span:has-text("输入地理位置")',
                'text="输入地理位置"',
                '[placeholder*="地理位置"]',
                '[placeholder*="位置"]',
                'input[placeholder*="地理位置"]',
                '.location-input',
                '[data-testid="location-input"]',
                'div.semi-select-selection',
                '.semi-select-selection-text:has-text("输入地理位置")'
            ]

            for selector in location_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    await page.click(selector)
                    self.logger.info(f"成功点击地理位置输入框: {selector}")
                    location_input_clicked = True
                    break
                except Exception as e:
                    self.logger.debug(f"尝试地理位置选择器 {selector} 失败: {str(e)}")
                    continue

            if not location_input_clicked:
                self.logger.warning("未找到地理位置输入框，跳过地理位置设置")
                return

            await asyncio.sleep(1)

            # 清空输入框并输入地理位置
            try:
                # 尝试多种清空方式
                await page.keyboard.press("Control+A")  # 全选
                await page.keyboard.press("Delete")  # 删除
                await asyncio.sleep(0.5)

                # 输入地理位置
                await page.keyboard.type(location)
                self.logger.info(f"已输入地理位置: {location}")
                await asyncio.sleep(2)  # 等待搜索结果

            except Exception as e:
                self.logger.warning(f"输入地理位置时出错: {str(e)}")
                # 尝试直接在输入框中输入
                try:
                    input_element = page.locator('input[placeholder*="地理位置"], input[type="text"]').first
                    await input_element.fill("")
                    await input_element.fill(location)
                    await asyncio.sleep(2)
                except Exception as e2:
                    self.logger.error(f"备用输入方法也失败: {str(e2)}")
                    return

            # 等待并选择下拉选项 - 多种方式
            option_clicked = False
            option_selectors = [
                'div[role="listbox"] [role="option"]',
                '.semi-select-option',
                'div[class*="option"]',
                'li[role="option"]',
                '.location-option',
                '[data-testid="location-option"]',
                'div[class*="dropdown"] div[class*="item"]',
                '.semi-list-item'
            ]

            for selector in option_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    options = page.locator(selector)
                    option_count = await options.count()

                    if option_count > 0:
                        # 尝试点击第一个选项
                        await options.first.click()
                        self.logger.info(f"成功选择地理位置选项: {selector}")
                        option_clicked = True
                        break
                except Exception as e:
                    self.logger.debug(f"尝试选项选择器 {selector} 失败: {str(e)}")
                    continue

            if not option_clicked:
                # 尝试按Enter键确认
                self.logger.warning("未找到下拉选项，尝试按Enter键确认")
                try:
                    await page.keyboard.press("Enter")
                    option_clicked = True
                except Exception as e:
                    self.logger.error(f"按Enter键确认失败: {str(e)}")

            if option_clicked:
                await asyncio.sleep(1)
                self.logger.info(f"地理位置设置完成: {location}")
            else:
                self.logger.warning("地理位置设置可能失败，但继续后续流程")

        except Exception as e:
            self.logger.error(f"设置地理位置时发生错误: {str(e)}")
            self.logger.info("地理位置设置失败，但不影响视频上传，继续后续流程")

    async def _handle_geolocation_permission(self, page: Page):
        """处理地理位置权限弹窗"""
        try:
            # 等待可能的权限弹窗
            await asyncio.sleep(1)

            # 尝试处理浏览器原生权限弹窗
            permission_selectors = [
                'button:has-text("允许")',
                'button:has-text("Allow")',
                'button:has-text("允许访问位置")',
                '[data-testid="permission-allow"]',
                '.permission-allow-btn'
            ]

            for selector in permission_selectors:
                try:
                    permission_btn = page.locator(selector)
                    if await permission_btn.count() > 0:
                        await permission_btn.click()
                        self.logger.info(f"已处理地理位置权限弹窗: {selector}")
                        await asyncio.sleep(1)
                        break
                except Exception as e:
                    self.logger.debug(f"尝试权限选择器 {selector} 失败: {str(e)}")
                    continue

        except Exception as e:
            self.logger.debug(f"处理地理位置权限时出错: {str(e)}")
            # 权限处理失败不影响主流程

    async def _set_third_party_sync(self, page: Page):
        """设置第三方平台同步"""
        try:
            third_part_element = '[class^="info"] > [class^="first-part"] div div.semi-switch'
            if await page.locator(third_part_element).count():
                # 检测是否是已选中状态
                if 'semi-switch-checked' not in await page.eval_on_selector(third_part_element, 'div => div.className'):
                    await page.locator(third_part_element).locator('input.semi-switch-native-control').click()
                    self.logger.info("已启用第三方平台同步")
        except Exception as e:
            self.logger.error(f"设置第三方平台同步时发生错误: {str(e)}")

    async def _set_schedule_time(self, page: Page, publish_date: datetime):
        """设置定时发布"""
        try:
            # 选择定时发布
            label_element = page.locator("[class^='radio']:has-text('定时发布')")
            await label_element.click()
            await asyncio.sleep(1)

            # 设置发布时间
            publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M")
            await page.locator('.semi-input[placeholder="日期和时间"]').click()
            await page.keyboard.press("Control+KeyA")
            await page.keyboard.type(str(publish_date_hour))
            await page.keyboard.press("Enter")

            self.logger.info(f"定时发布时间设置为: {publish_date_hour}")
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.error(f"设置定时发布时发生错误: {str(e)}")

    async def _publish_video(self, page: Page):
        """发布视频"""
        self.logger.info("正在发布视频...")
        while True:
            try:
                publish_button = page.get_by_role('button', name="发布", exact=True)
                if await publish_button.count():
                    await publish_button.click()

                # 等待跳转到作品管理页面
                await page.wait_for_url("https://creator.douyin.com/creator-micro/content/manage**", timeout=3000)
                self.logger.info("视频发布成功")
                break
            except:
                self.logger.info("视频正在发布中...")
                await page.screenshot(full_page=True)
                await asyncio.sleep(0.5)

    async def _setup_page_permissions(self, page: Page):
        """设置页面权限处理"""
        try:
            # 监听权限请求并自动允许
            async def handle_permission_request(request):
                self.logger.info(f"收到权限请求: {request.name}")
                await request.allow()

            # 监听对话框（包括权限弹窗）
            async def handle_dialog(dialog):
                self.logger.info(f"收到对话框: {dialog.type} - {dialog.message}")
                if "位置" in dialog.message or "location" in dialog.message.lower():
                    await dialog.accept()
                else:
                    await dialog.dismiss()

            # 绑定事件监听器
            page.on("dialog", handle_dialog)

            # 注入自动处理权限的脚本
            await page.add_init_script(
                """
                // 重写 geolocation API 以避免权限弹窗
                if (navigator.geolocation) {
                    const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition;
                    navigator.geolocation.getCurrentPosition = function(success, error, options) {
                        // 直接返回北京坐标
                        success({
                            coords: {
                                latitude: 39.9042,
                                longitude: 116.4074,
                                accuracy: 50
                            },
                            timestamp: Date.now()
                        });
                    };
                }

                // 自动处理权限弹窗
                const originalConfirm = window.confirm;
                window.confirm = function(message) {
                    if (message.includes('位置') || message.includes('location')) {
                        return true;
                    }
                    return originalConfirm.call(this, message);
                };
            """
                )

            self.logger.info("页面权限处理设置完成")

        except Exception as e:
            self.logger.warning(f"设置页面权限处理时发生错误: {str(e)}")

    async def _set_init_script(self, context):
        """设置初始化脚本"""
        try:
            stealth_js_path = Path(__file__).parent / "stealth.min.js"
            if stealth_js_path.exists():
                await context.add_init_script(path=str(stealth_js_path))
            return context
        except Exception as e:
            self.logger.warning(f"设置初始化脚本时发生错误: {str(e)}")
            return context
