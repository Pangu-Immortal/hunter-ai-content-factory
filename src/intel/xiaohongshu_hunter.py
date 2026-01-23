"""
Hunter AI 内容工厂 - 小红书采集模块

功能：
- 基于 httpx + Cookie 采集小红书笔记
- 搜索指定关键词的笔记
- 获取热门笔记列表
- AI 生成种草/测评文章

使用方法：
    from src.intel.xiaohongshu_hunter import XiaohongshuHunter

    hunter = XiaohongshuHunter()
    notes = await hunter.get_hot_notes("AI工具")
    article = await hunter.generate_article(notes)

Cookie 获取方法：
    1. 浏览器登录小红书 (https://www.xiaohongshu.com)
    2. F12 打开开发者工具 → Application → Cookies
    3. 复制所有 Cookie 到 config.yaml 的 xiaohongshu.cookies 字段

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import json
import re
import hashlib
import time
import random
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode

import httpx

from src.config import settings, ROOT_DIR
from src.utils.logger import get_logger
from src.utils.ai_client import get_ai_client
from src.intel.utils import create_article_dir, get_article_file_path, get_today_str

logger = get_logger("hunter.intel.xiaohongshu")


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
    author_id: str                        # 作者 ID
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
# 小红书采集器
# ═══════════════════════════════════════════════════════════════════════════════

class XiaohongshuHunter:
    """
    小红书采集器 - 基于 httpx + Cookie

    核心功能：
    1. 搜索笔记 - 按关键词搜索
    2. 获取热门笔记 - 获取指定话题的热门内容
    3. AI 生成文章 - 基于采集内容生成公众号文章
    """

    # API 基础配置
    BASE_URL = "https://edith.xiaohongshu.com"
    WEB_URL = "https://www.xiaohongshu.com"

    # 请求头模板
    DEFAULT_HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "referer": "https://www.xiaohongshu.com/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    def __init__(self):
        """初始化采集器"""
        self.cookies = self._load_cookies()
        self.client: Optional[httpx.AsyncClient] = None

    def _load_cookies(self) -> dict:
        """
        加载 Cookie

        优先级：
        1. config.yaml 中的 xiaohongshu.cookies
        2. data/auth/xiaohongshu_cookies.json 文件
        """
        # 从配置文件加载
        if hasattr(settings, 'xiaohongshu') and settings.xiaohongshu.cookies:
            cookie_str = settings.xiaohongshu.cookies
            return self._parse_cookie_string(cookie_str)

        # 从文件加载
        cookie_file = ROOT_DIR / "data" / "auth" / "xiaohongshu_cookies.json"
        if cookie_file.exists():
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"读取 Cookie 文件失败: {e}")

        return {}

    def _parse_cookie_string(self, cookie_str: str) -> dict:
        """解析 Cookie 字符串为字典"""
        cookies = {}
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        return cookies

    def save_cookies(self, cookies: dict) -> None:
        """保存 Cookie 到文件"""
        cookie_dir = ROOT_DIR / "data" / "auth"
        cookie_dir.mkdir(parents=True, exist_ok=True)

        cookie_file = cookie_dir / "xiaohongshu_cookies.json"
        with open(cookie_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        logger.info(f"Cookie 已保存到 {cookie_file}")

    def is_logged_in(self) -> bool:
        """检查是否已登录（Cookie 是否有效）"""
        required_keys = ['web_session', 'a1']
        return all(key in self.cookies for key in required_keys)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                cookies=self.cookies,
                timeout=30.0,
                follow_redirects=True,
            )
        return self.client

    async def close(self) -> None:
        """关闭客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None

    def _generate_x_s(self, url: str, data: Optional[dict] = None) -> str:
        """
        生成 X-s 签名

        注意：这是一个简化版本，实际小红书的签名算法更复杂
        如果遇到签名验证问题，可能需要更新此方法
        """
        # 简化签名：时间戳 + 随机数
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        sign_str = f"{timestamp}{random_str}{url}"

        if data:
            sign_str += json.dumps(data, separators=(',', ':'), ensure_ascii=False)

        return hashlib.md5(sign_str.encode()).hexdigest()

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        sort: str = "general",  # general: 综合, time_descending: 最新, popularity_descending: 最热
    ) -> list[XhsNote]:
        """
        搜索小红书笔记

        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            sort: 排序方式

        Returns:
            笔记列表
        """
        if not self.is_logged_in():
            logger.error("未登录，请先配置 Cookie")
            return []

        client = await self._get_client()

        # 构建搜索请求
        api_url = "/api/sns/web/v1/search/notes"
        params = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "note_type": 0,  # 0: 全部, 1: 视频, 2: 图文
        }

        try:
            # 添加签名
            headers = {
                "x-s": self._generate_x_s(api_url, params),
                "x-t": str(int(time.time() * 1000)),
            }

            response = await client.post(
                f"{self.BASE_URL}{api_url}",
                json=params,
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(f"搜索请求失败: {response.status_code}")
                return []

            data = response.json()

            if data.get("success") is False:
                logger.error(f"搜索失败: {data.get('msg', '未知错误')}")
                return []

            # 解析结果
            notes = []
            items = data.get("data", {}).get("items", [])

            for item in items:
                note_card = item.get("note_card", {})
                user = note_card.get("user", {})

                note = XhsNote(
                    note_id=item.get("id", ""),
                    title=note_card.get("display_title", ""),
                    desc=note_card.get("desc", ""),
                    author=user.get("nickname", ""),
                    author_id=user.get("user_id", ""),
                    likes=note_card.get("interact_info", {}).get("liked_count", 0),
                    collects=note_card.get("interact_info", {}).get("collected_count", 0),
                    comments=note_card.get("interact_info", {}).get("comment_count", 0),
                    url=f"{self.WEB_URL}/explore/{item.get('id', '')}",
                )

                # 提取图片
                if "image_list" in note_card:
                    note.images = [
                        img.get("url_default", "") or img.get("url", "")
                        for img in note_card.get("image_list", [])
                    ]

                # 提取标签
                if "tag_list" in note_card:
                    note.tags = [tag.get("name", "") for tag in note_card.get("tag_list", [])]

                notes.append(note)

            logger.info(f"搜索 '{keyword}' 找到 {len(notes)} 条笔记")
            return notes

        except Exception as e:
            logger.error(f"搜索异常: {e}")
            return []

    async def get_note_detail(self, note_id: str) -> Optional[XhsNote]:
        """
        获取笔记详情

        Args:
            note_id: 笔记 ID

        Returns:
            笔记详情
        """
        if not self.is_logged_in():
            logger.error("未登录，请先配置 Cookie")
            return None

        client = await self._get_client()

        api_url = "/api/sns/web/v1/feed"
        params = {
            "source_note_id": note_id,
        }

        try:
            headers = {
                "x-s": self._generate_x_s(api_url, params),
                "x-t": str(int(time.time() * 1000)),
            }

            response = await client.post(
                f"{self.BASE_URL}{api_url}",
                json=params,
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(f"获取笔记详情失败: {response.status_code}")
                return None

            data = response.json()

            if data.get("success") is False:
                logger.error(f"获取笔记详情失败: {data.get('msg', '未知错误')}")
                return None

            # 解析详情
            items = data.get("data", {}).get("items", [])
            if not items:
                return None

            note_data = items[0].get("note_card", {})
            user = note_data.get("user", {})
            interact = note_data.get("interact_info", {})

            note = XhsNote(
                note_id=note_id,
                title=note_data.get("title", ""),
                desc=note_data.get("desc", ""),
                author=user.get("nickname", ""),
                author_id=user.get("user_id", ""),
                likes=self._parse_count(interact.get("liked_count", "0")),
                collects=self._parse_count(interact.get("collected_count", "0")),
                comments=self._parse_count(interact.get("comment_count", "0")),
                url=f"{self.WEB_URL}/explore/{note_id}",
            )

            # 提取图片
            if "image_list" in note_data:
                note.images = [
                    img.get("url_default", "") or img.get("info_list", [{}])[0].get("url", "")
                    for img in note_data.get("image_list", [])
                ]

            # 提取标签
            if "tag_list" in note_data:
                note.tags = [tag.get("name", "") for tag in note_data.get("tag_list", [])]

            # 发布时间
            if "time" in note_data:
                try:
                    note.created_at = datetime.fromtimestamp(note_data["time"] / 1000)
                except Exception:
                    pass

            return note

        except Exception as e:
            logger.error(f"获取笔记详情异常: {e}")
            return None

    def _parse_count(self, count_str: str) -> int:
        """解析数量字符串（如 '1.2万'）"""
        if isinstance(count_str, int):
            return count_str

        count_str = str(count_str).strip()
        if not count_str:
            return 0

        try:
            if '万' in count_str:
                return int(float(count_str.replace('万', '')) * 10000)
            elif 'w' in count_str.lower():
                return int(float(count_str.lower().replace('w', '')) * 10000)
            else:
                return int(count_str)
        except Exception:
            return 0

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
            热门笔记列表（按热度排序）
        """
        logger.info(f"开始获取 '{keyword}' 相关热门笔记...")

        # 搜索笔记
        notes = await self.search(keyword, page_size=min(count * 2, 40), sort="popularity_descending")

        if not notes:
            logger.warning(f"未找到 '{keyword}' 相关笔记")
            return []

        # 按热度排序（点赞 + 收藏 + 评论）
        notes.sort(key=lambda x: x.likes + x.collects + x.comments, reverse=True)

        # 取前 N 条
        hot_notes = notes[:count]

        logger.info(f"获取到 {len(hot_notes)} 条热门笔记")
        return hot_notes

    async def generate_article(
        self,
        notes: list[XhsNote],
        style: str = "种草",  # 种草 / 测评 / 盘点
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
内容：{note.desc[:500]}...
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
            from src.utils.ai_client import get_ai_client

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

        # 检查登录状态
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

            # 2. 生成文章
            article = await self.generate_article(notes, style)

            if not article:
                return {
                    "success": False,
                    "error": "文章生成失败",
                    "notes": [n.to_dict() for n in notes],
                    "article": "",
                }

            # 3. 提取标题并创建文章目录
            article_lines = article.split('\n')
            title = keyword  # 默认使用关键词
            for line in article_lines:
                if line.startswith('#'):
                    title = line.replace('#', '').strip()[:30]
                    break

            article_dir = create_article_dir(title)
            logger.info(f"文章目录已创建: {article_dir}")

            # 4. 保存文章
            article_path = get_article_file_path(article_dir, "article.md")
            article_path.write_text(article, encoding="utf-8")
            logger.info(f"文章已保存: {article_path}")

            # 4. 保存元数据
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
                "keyword": keyword,
                "style": style,
                "article_dir": str(article_dir),
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

    parser = argparse.ArgumentParser(description="小红书采集器")
    parser.add_argument("keyword", nargs="?", default="AI工具", help="搜索关键词")
    parser.add_argument("-n", "--count", type=int, default=5, help="采集数量")
    parser.add_argument("-s", "--style", default="种草", help="文章风格")
    args = parser.parse_args()

    hunter = XiaohongshuHunter()
    result = await hunter.run(args.keyword, args.count, args.style)

    if result["success"]:
        print(f"\n{'=' * 50}")
        print("✅ 采集成功！")
        print(f"{'=' * 50}\n")
        print(result["article"][:500] + "...\n")  # 只预览前 500 字

        # 输出保存位置
        print(f"📁 文章目录: {result.get('article_dir', 'N/A')}")
    else:
        print(f"\n❌ 采集失败: {result['error']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
