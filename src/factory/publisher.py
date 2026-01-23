"""
Hunter AI 内容工厂 - 文章推送模块

功能：
- 通过 PushPlus 推送文章到微信
- 支持 Markdown 格式
- 自动生成推送标题和摘要

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import datetime
from pathlib import Path

from rich.console import Console

from src.config import settings
from src.intel.utils import create_http_client

# 终端输出美化
console = Console()


def push_article_to_wechat(
    title: str,
    content: str,
    summary: str = "",
    template: str = "markdown"
) -> dict:
    """
    推送文章到微信

    Args:
        title: 文章标题
        content: 文章内容（Markdown 格式）
        summary: 文章摘要
        template: 模板类型

    Returns:
        dict: 推送结果
    """
    token = settings.push.token

    if not token:
        console.print("[yellow]⚠️ PushPlus Token 未配置，跳过推送[/yellow]")
        return {
            "push_status": "skipped",
            "error_message": "Token 未配置"
        }

    today = datetime.date.today().strftime("%Y-%m-%d")

    # 格式化推送内容
    formatted_content = f"## 📅 {today} 新文发布\n\n"
    if summary:
        formatted_content += f"**摘要**: {summary}\n\n---\n\n"
    formatted_content += content

    try:
        with create_http_client(timeout=15.0) as client:
            response = client.post(
                'https://www.pushplus.plus/send',
                json={
                    "token": token,
                    "title": f"【成稿】{title[:30]}",
                    "content": formatted_content,
                    "template": template
                }
            )
            result = response.json()

            if result.get('code') == 200:
                console.print(f"[green]✅ 推送成功！消息ID: {result.get('data')}[/green]")
                return {
                    "push_status": "success",
                    "push_time": datetime.datetime.now().isoformat(),
                    "message_id": str(result.get('data', '')),
                    "error_message": ""
                }
            else:
                console.print(f"[red]❌ 推送失败: {result.get('msg')}[/red]")
                return {
                    "push_status": "failed",
                    "push_time": datetime.datetime.now().isoformat(),
                    "message_id": "",
                    "error_message": result.get('msg', '未知错误')
                }

    except Exception as e:
        console.print(f"[red]❌ 推送出错: {e}[/red]")
        return {
            "push_status": "error",
            "push_time": datetime.datetime.now().isoformat(),
            "message_id": "",
            "error_message": str(e)
        }


def push_article_from_file(file_path: str | Path, title: str = "") -> dict:
    """
    从文件读取文章并推送

    Args:
        file_path: 文章文件路径
        title: 文章标题（可选，默认从文件名提取）

    Returns:
        dict: 推送结果
    """
    path = Path(file_path)

    if not path.exists():
        console.print(f"[red]❌ 文件不存在: {path}[/red]")
        return {
            "push_status": "error",
            "error_message": f"文件不存在: {path}"
        }

    # 读取文件内容
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 如果没有指定标题，从文件名提取
    if not title:
        title = path.stem.replace('_', ' ')

    return push_article_to_wechat(title=title, content=content)


def main():
    """测试推送功能"""
    console.print("[bold magenta]📨 文章推送测试[/bold magenta]\n")

    test_content = """
# 测试文章

这是一篇测试文章。

## 第一节

这里是第一节的内容。

## 第二节

这里是第二节的内容。

---

感谢阅读！
"""

    result = push_article_to_wechat(
        title="测试文章",
        content=test_content,
        summary="这是一篇测试文章的摘要"
    )

    console.print(f"\n推送结果: {result}")


if __name__ == "__main__":
    main()
