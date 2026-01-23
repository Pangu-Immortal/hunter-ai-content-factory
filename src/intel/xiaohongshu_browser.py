"""
Hunter AI 内容工厂 - 小红书浏览器采集模块

功能：
- 基于 Playwright 浏览器自动化采集小红书笔记
- 绕过 X-s 签名验证问题
- 支持 Cookie 注入登录

使用方法：
    from src.intel.xiaohongshu_browser import XiaohongshuBrowser

    browser = XiaohongshuBrowser()
    notes = await browser.search("AI工具")

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import json
import re
import random
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.config import settings, ROOT_DIR
from src.utils.logger import get_logger
from src.utils.ai_client import get_ai_client
from src.intel.utils import create_article_dir, get_article_file_path, get_today_str

logger = get_logger("hunter.intel.xiaohongshu_browser")


# ═══════════════════════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class XhsNote:
    """小红书笔记数据"""
    note_id: str                          # 笔记 ID
    title: str                            # 标题
    desc: str                             # 描述/正文
    author: str                           # 作者昵称
    author_id: str = ""                   # 作者 ID
    likes: int = 0                        # 点赞数
    collects: int = 0                     # 收藏数
    comments: int = 0                     # 评论数
    images: list[str] = field(default_factory=list)  # 图片列表
    tags: list[str] = field(default_factory=list)    # 标签列表
    url: str = ""                         # 笔记链接
    created_at: Optional[datetime] = None # 发布时间

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "note_id": self.note_id,
            "title": self.title,
            "desc": self.desc,
            "author": self.author,
            "author_id": self.author_id,
            "likes": self.likes,
            "collects": self.collects,
            "comments": self.comments,
            "images": self.images,
            "tags": self.tags,
            "url": self.url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 小红书浏览器采集器
# ═══════════════════════════════════════════════════════════════════════════════

class XiaohongshuBrowser:
    """
    小红书浏览器采集器 - 基于 Playwright

    核心功能：
    1. 浏览器模拟 - 绕过反爬验证
    2. Cookie 注入 - 实现登录态
    3. 页面解析 - 提取笔记内容
    """

    BASE_URL = "https://www.xiaohongshu.com"

    def __init__(self):
        """初始化采集器"""
        self.cookies = self._load_cookies()
        self.browser = None
        self.context = None
        self.page = None

    def _load_cookies(self) -> list[dict]:
        """
        加载 Cookie 并转换为 Playwright 格式

        Returns:
            Playwright 格式的 cookies 列表
        """
        # 从配置文件加载
        if hasattr(settings, 'xiaohongshu') and settings.xiaohongshu.cookies:
            cookie_str = settings.xiaohongshu.cookies
            return self._parse_cookie_string(cookie_str)

        return []

    def _parse_cookie_string(self, cookie_str: str) -> list[dict]:
        """
        解析 Cookie 字符串为 Playwright 格式

        Args:
            cookie_str: 如 "a1=xxx; web_session=xxx"

        Returns:
            Playwright cookies 列表
        """
        cookies = []
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies.append({
                    "name": key.strip(),
                    "value": value.strip(),
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                })
        return cookies

    def is_logged_in(self) -> bool:
        """检查是否已配置 Cookie"""
        cookie_names = [c["name"] for c in self.cookies]
        required = ['web_session', 'a1']
        return all(name in cookie_names for name in required)

    async def _init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright

        logger.info("正在启动浏览器...")

        self._playwright = await async_playwright().start()

        # 启动浏览器（无头模式）
        self.browser = await self._playwright.chromium.launch(
            headless=True,  # 无头模式
            args=[
                '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # 创建上下文（模拟真实浏览器）
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )

        # 注入 Cookie
        if self.cookies:
            await self.context.add_cookies(self.cookies)
            logger.info(f"已注入 {len(self.cookies)} 个 Cookie")

        # 创建页面
        self.page = await self.context.new_page()

        # 隐藏 WebDriver 特征
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        logger.info("浏览器启动完成")

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, '_playwright') and self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("浏览器已关闭")

    async def search(
        self,
        keyword: str,
        count: int = 10,
        sort: str = "popularity_descending",  # general, time_descending, popularity_descending
    ) -> list[XhsNote]:
        """
        搜索小红书笔记

        Args:
            keyword: 搜索关键词
            count: 获取数量
            sort: 排序方式

        Returns:
            笔记列表
        """
        if not self.page:
            await self._init_browser()

        logger.info(f"搜索关键词: {keyword}")

        try:
            # 访问搜索页
            search_url = f"{self.BASE_URL}/search_result?keyword={keyword}&source=web_search_result_notes"
            await self.page.goto(search_url, wait_until='networkidle', timeout=30000)

            # 等待页面加载
            await asyncio.sleep(2)

            # 检查是否需要登录
            page_content = await self.page.content()
            if '登录' in page_content and '注册' in page_content and len(page_content) < 5000:
                logger.warning("检测到登录页面，Cookie 可能已过期")
                return []

            # 滚动加载更多内容
            for _ in range(3):
                await self.page.evaluate('window.scrollBy(0, 1000)')
                await asyncio.sleep(1)

            # 解析笔记列表
            notes = await self._parse_search_results(count)

            logger.info(f"搜索 '{keyword}' 找到 {len(notes)} 条笔记")
            return notes

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    async def _parse_search_results(self, count: int) -> list[XhsNote]:
        """
        解析搜索结果页面

        Args:
            count: 最大获取数量

        Returns:
            笔记列表
        """
        notes = []

        try:
            # 等待笔记卡片加载
            await self.page.wait_for_selector('section.note-item, div[class*="note-item"]', timeout=10000)

            # 获取所有笔记卡片
            note_elements = await self.page.query_selector_all('section.note-item, div[class*="note-item"]')

            for element in note_elements[:count]:
                try:
                    note = await self._parse_note_card(element)
                    if note:
                        notes.append(note)
                except Exception as e:
                    logger.debug(f"解析笔记卡片失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"解析搜索结果失败: {e}")

        return notes

    async def _parse_note_card(self, element) -> Optional[XhsNote]:
        """
        解析单个笔记卡片

        Args:
            element: 笔记卡片元素

        Returns:
            XhsNote 对象
        """
        try:
            # 获取链接和 ID
            link_elem = await element.query_selector('a[href*="/explore/"], a[href*="/search_result/"]')
            if not link_elem:
                link_elem = await element.query_selector('a')

            href = await link_elem.get_attribute('href') if link_elem else ""
            note_id = ""
            if '/explore/' in href:
                note_id = href.split('/explore/')[-1].split('?')[0]
            elif '/search_result/' in href:
                note_id = href.split('/')[-1].split('?')[0]

            # 获取标题
            title_elem = await element.query_selector('span.title, div[class*="title"], a.title')
            title = await title_elem.inner_text() if title_elem else ""

            # 获取作者
            author_elem = await element.query_selector('span.name, div[class*="author"], span[class*="name"]')
            author = await author_elem.inner_text() if author_elem else ""

            # 获取点赞数
            likes_elem = await element.query_selector('span.count, span[class*="like"], span[class*="count"]')
            likes_text = await likes_elem.inner_text() if likes_elem else "0"
            likes = self._parse_count(likes_text)

            # 获取封面图
            img_elem = await element.query_selector('img')
            cover_url = await img_elem.get_attribute('src') if img_elem else ""

            if not note_id and not title:
                return None

            return XhsNote(
                note_id=note_id or f"unknown_{random.randint(1000, 9999)}",
                title=title.strip() if title else "无标题",
                desc="",  # 列表页无完整描述
                author=author.strip() if author else "未知作者",
                likes=likes,
                images=[cover_url] if cover_url else [],
                url=f"{self.BASE_URL}/explore/{note_id}" if note_id else "",
            )

        except Exception as e:
            logger.debug(f"解析笔记卡片异常: {e}")
            return None

    def _parse_count(self, count_str: str) -> int:
        """解析数量字符串（如 '1.2万'）"""
        if not count_str:
            return 0

        count_str = str(count_str).strip()

        try:
            # 移除非数字字符（保留数字、小数点、万/w）
            count_str = re.sub(r'[^\d.万wW]', '', count_str)

            if '万' in count_str or 'w' in count_str.lower():
                num = float(count_str.replace('万', '').replace('w', '').replace('W', ''))
                return int(num * 10000)
            elif count_str:
                return int(float(count_str))
            else:
                return 0
        except Exception:
            return 0

    async def get_note_detail(self, note_id: str) -> Optional[XhsNote]:
        """
        获取笔记详情

        Args:
            note_id: 笔记 ID

        Returns:
            笔记详情
        """
        if not self.page:
            await self._init_browser()

        try:
            url = f"{self.BASE_URL}/explore/{note_id}"
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)

            # 解析详情页
            # 标题
            title_elem = await self.page.query_selector('div#detail-title, h1[class*="title"]')
            title = await title_elem.inner_text() if title_elem else ""

            # 正文
            desc_elem = await self.page.query_selector('div#detail-desc, div[class*="desc"], div[class*="content"]')
            desc = await desc_elem.inner_text() if desc_elem else ""

            # 作者
            author_elem = await self.page.query_selector('span.username, a[class*="name"]')
            author = await author_elem.inner_text() if author_elem else ""

            # 互动数据
            likes_elem = await self.page.query_selector('span[class*="like"] span, span.count')
            likes = self._parse_count(await likes_elem.inner_text() if likes_elem else "0")

            # 图片列表
            images = []
            img_elems = await self.page.query_selector_all('div[class*="swiper"] img, div[class*="carousel"] img')
            for img in img_elems:
                src = await img.get_attribute('src')
                if src:
                    images.append(src)

            # 标签
            tags = []
            tag_elems = await self.page.query_selector_all('a[href*="/search_result?keyword="]')
            for tag in tag_elems:
                tag_text = await tag.inner_text()
                if tag_text and tag_text.startswith('#'):
                    tags.append(tag_text[1:])

            return XhsNote(
                note_id=note_id,
                title=title.strip(),
                desc=desc.strip(),
                author=author.strip(),
                likes=likes,
                images=images,
                tags=tags,
                url=url,
            )

        except Exception as e:
            logger.error(f"获取笔记详情失败: {e}")
            return None

    async def get_hot_notes(
        self,
        keyword: str,
        count: int = 10,
    ) -> list[XhsNote]:
        """
        获取热门笔记

        Args:
            keyword: 搜索关键词
            count: 获取数量

        Returns:
            热门笔记列表
        """
        logger.info(f"开始获取 '{keyword}' 相关热门笔记...")

        notes = await self.search(keyword, count=count * 2)

        if not notes:
            logger.warning(f"未找到 '{keyword}' 相关笔记")
            return []

        # 按热度排序
        notes.sort(key=lambda x: x.likes + x.collects + x.comments, reverse=True)

        hot_notes = notes[:count]
        logger.info(f"获取到 {len(hot_notes)} 条热门笔记")

        return hot_notes

    async def generate_article(
        self,
        notes: list[XhsNote],
        style: str = "种草",
    ) -> str:
        """
        基于笔记内容生成公众号文章

        Args:
            notes: 笔记列表
            style: 文章风格

        Returns:
            生成的文章内容
        """
        if not notes:
            return ""

        # 准备笔记摘要
        notes_summary = []
        for i, note in enumerate(notes, 1):
            summary = f"""
【笔记{i}】
标题：{note.title}
作者：{note.author}
内容：{note.desc[:500] if note.desc else '（无详细内容）'}
点赞：{note.likes} | 收藏：{note.collects} | 评论：{note.comments}
标签：{', '.join(note.tags) if note.tags else '无'}
"""
            notes_summary.append(summary)

        # 生成文章
        prompt = f"""你是一位资深的公众号内容创作者，擅长将小红书热门内容改编为公众号文章。

请根据以下小红书热门笔记，生成一篇{style}风格的公众号文章。

## 小红书热门笔记

{''.join(notes_summary)}

## 写作要求

1. **标题**：吸引人但不标题党，体现价值
2. **开头**：快速切入主题，引发共鸣
3. **正文**：
   - 整合多个笔记的核心观点
   - 加入你的专业分析和见解
   - 保持口语化、有网感
   - 避免直接复制原文
4. **结尾**：引导互动，邀请读者留言
5. **字数**：1500-2500 字

## 格式要求

```
# 标题

正文内容...

---
你觉得这些xxx怎么样？欢迎在评论区分享你的看法~
```

请直接输出文章内容：
"""

        try:
            ai_client = get_ai_client()
            response = ai_client.generate_sync(prompt)
            article = response.text.strip()

            # 清理 markdown 代码块标记
            if article.startswith("```"):
                article = re.sub(r'^```\w*\n?', '', article)
                article = re.sub(r'\n?```$', '', article)

            logger.info(f"文章生成完成，字数：{len(article)}")
            return article

        except Exception as e:
            logger.error(f"文章生成失败: {e}")
            return ""

    async def run(
        self,
        keyword: str = "AI工具",
        count: int = 5,
        style: str = "种草",
    ) -> dict:
        """
        完整执行流程

        Args:
            keyword: 搜索关键词
            count: 采集笔记数量
            style: 文章风格

        Returns:
            执行结果
        """
        logger.info(f"开始小红书采集任务: 关键词={keyword}, 数量={count}, 风格={style}")

        if not self.is_logged_in():
            return {
                "success": False,
                "error": "未配置小红书 Cookie，请在 config.yaml 中配置 xiaohongshu.cookies",
                "notes": [],
                "article": "",
            }

        try:
            # 1. 获取热门笔记
            notes = await self.get_hot_notes(keyword, count)

            if not notes:
                return {
                    "success": False,
                    "error": f"未找到 '{keyword}' 相关笔记",
                    "notes": [],
                    "article": "",
                }

            # 2. 获取部分笔记的详情（丰富内容）
            for i, note in enumerate(notes[:3]):  # 只获取前3条的详情
                if note.note_id and note.note_id != "unknown":
                    detail = await self.get_note_detail(note.note_id)
                    if detail and detail.desc:
                        notes[i].desc = detail.desc
                        notes[i].tags = detail.tags
                    await asyncio.sleep(1)  # 避免请求过快

            # 3. 生成文章
            article = await self.generate_article(notes, style)

            if not article:
                return {
                    "success": False,
                    "error": "文章生成失败",
                    "notes": [n.to_dict() for n in notes],
                    "article": "",
                }

            # 4. 提取标题并创建文章目录
            article_lines = article.split('\n')
            title = keyword
            for line in article_lines:
                if line.startswith('#'):
                    title = line.replace('#', '').strip()[:30]
                    break

            article_dir = create_article_dir(title)
            logger.info(f"文章目录已创建: {article_dir}")

            # 5. 保存文章
            article_path = get_article_file_path(article_dir, "article.md")
            article_path.write_text(article, encoding="utf-8")
            logger.info(f"文章已保存: {article_path}")

            # 5. 保存元数据
            metadata = {
                "title": title,
                "keyword": keyword,
                "style": style,
                "date": get_today_str(),
                "notes_count": len(notes),
                "notes": [n.to_dict() for n in notes],
            }
            metadata_path = get_article_file_path(article_dir, "metadata.json")
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.info(f"元数据已保存: {metadata_path}")

            return {
                "success": True,
                "error": None,
                "notes": [n.to_dict() for n in notes],
                "article": article,
                "article_title": title,
                "article_content": article,
                "keyword": keyword,
                "style": style,
                "output_path": str(article_dir),
            }

        except Exception as e:
            logger.error(f"执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "notes": [],
                "article": "",
            }

        finally:
            await self.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="小红书浏览器采集器")
    parser.add_argument("keyword", nargs="?", default="AI工具", help="搜索关键词")
    parser.add_argument("-n", "--count", type=int, default=5, help="采集数量")
    parser.add_argument("-s", "--style", default="种草", help="文章风格")
    args = parser.parse_args()

    browser = XiaohongshuBrowser()
    result = await browser.run(args.keyword, args.count, args.style)

    if result["success"]:
        print(f"\n{'=' * 50}")
        print("✅ 采集成功！")
        print(f"{'=' * 50}\n")
        print(result["article"][:500] + "...\n")

        print(f"📁 文章目录: {result.get('output_path', 'N/A')}")
    else:
        print(f"\n❌ 采集失败: {result['error']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
