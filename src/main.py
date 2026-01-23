"""
Hunter AI 内容工厂 - CLI 主入口

功能：
- 一键启动：uv run hunter run
- 支持多种内容模板：github / pain / news / xhs / auto
- 全自动执行流程

使用方法：
    uv run hunter run              # 默认运行 github 模板
    uv run hunter run --type pain  # 运行痛点模板
    uv run hunter run --type news  # 运行资讯模板
    uv run hunter run --type auto  # 运行自动创作模式
    uv run hunter --help           # 查看帮助

GitHub: https://github.com/Pangu-Immortal/hunter-ai-content-factory
Author: Pangu-Immortal
"""

import asyncio
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 终端输出美化
console = Console()


@click.group()
@click.version_option(version="3.0.0", prog_name="Hunter AI")
def cli():
    """
    🦅 Hunter AI 内容工厂 v3.0

    一键生成高质量公众号文章，全自动执行。

    \b
    快速开始：
        uv run hunter run              # 默认：GitHub 开源推荐
        uv run hunter run --type pain  # 痛点解决方案
        uv run hunter run --type news  # 资讯快报
        uv run hunter run --type auto  # 自动创作模式

    \b
    查看帮助：
        uv run hunter --help
        uv run hunter run --help
    """
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# 核心命令：一键启动
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
@click.option(
    '--type', '-t',
    type=click.Choice(['github', 'pain', 'news', 'xhs', 'auto']),
    default='github',
    help='内容类型：github(开源推荐) / pain(痛点方案) / news(资讯快报) / xhs(小红书热门) / auto(自动创作)'
)
@click.option('--dry-run', is_flag=True, help='试运行（不推送到微信）')
def run(type, dry_run):
    """
    🚀 一键启动 - 全自动生成并推送文章

    \b
    内容类型说明：
      github - GitHub 开源推荐（2个项目 + 1个深度解读）
      pain   - 痛点解决方案（从 Twitter + Reddit 采集用户痛点）
      news   - 资讯快报（5平台热点汇总）
      xhs    - 小红书热门（采集热门笔记生成种草文章）
      auto   - 自动创作（全自动 Intel→分析→生成 流水线）

    \b
    示例：
      uv run hunter run                # 默认运行 github
      uv run hunter run -t github      # GitHub 开源推荐
      uv run hunter run -t pain        # 痛点解决方案
      uv run hunter run -t news        # 资讯快报
      uv run hunter run -t xhs         # 小红书热门
      uv run hunter run -t auto        # 自动创作模式
      uv run hunter run --dry-run      # 试运行，不推送
    """
    # 显示启动信息
    console.print(Panel.fit(
        f"[bold cyan]🦅 Hunter AI 内容工厂[/bold cyan]\n"
        f"[dim]模板: {type} | 推送: {'禁用' if dry_run else '启用'}[/dim]",
        border_style="cyan"
    ))

    # 临时禁用推送（如果 dry-run）
    if dry_run:
        from src.config import settings
        settings.push.enabled = False
        console.print("[yellow]⚠️ 试运行模式：不会推送到微信[/yellow]\n")

    # 获取并执行模板
    from src.templates import get_template

    try:
        template = get_template(type)
        result = asyncio.run(template.run())

        # 显示结果
        if result.success:
            console.print("\n[bold green]✅ 执行完成！[/bold green]")
            console.print(f"   标题: {result.title}")
            console.print(f"   推送: {result.push_status}")
        else:
            console.print(f"\n[bold red]❌ 执行失败: {result.error}[/bold red]")

    except Exception as e:
        console.print(f"\n[bold red]❌ 运行失败: {e}[/bold red]")
        raise


@cli.command()
def templates():
    """📋 列出所有可用模板"""
    from src.templates import TEMPLATES

    table = Table(title="可用模板", show_header=True, header_style="bold cyan")
    table.add_column("名称", style="green")
    table.add_column("描述")
    table.add_column("命令示例")

    for name, desc in TEMPLATES.items():
        table.add_row(name, desc, f"uv run hunter run -t {name}")

    console.print(table)


@cli.command()
@click.option('--port', '-p', default=7860, help='Web UI 端口（默认 7860）')
@click.option('--share', '-s', is_flag=True, help='开启外链分享')
@click.option('--no-browser', is_flag=True, help='不自动打开浏览器')
def web(port, share, no_browser):
    """
    🌐 启动 Web UI - 可视化操作界面

    \b
    功能说明：
      - 可视化的 6-Skill 工作流操作
      - 多平台情报采集
      - 内容违禁词检查
      - 配置管理

    \b
    示例：
      uv run hunter web              # 默认启动
      uv run hunter web -p 8080      # 指定端口
      uv run hunter web --share      # 开启外链分享
      uv run hunter web --no-browser # 不自动打开浏览器
    """
    console.print(Panel.fit(
        "[bold cyan]🌐 Hunter AI Web UI[/bold cyan]\n"
        f"[dim]端口: {port} | 分享: {'启用' if share else '禁用'}[/dim]",
        border_style="cyan"
    ))

    from src.gradio_app import create_app

    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=share,
        show_error=True,
        inbrowser=not no_browser,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 工具命令
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command()
def config():
    """⚙️ 显示当前配置"""
    console.print(Panel.fit("⚙️ 当前配置", style="bold cyan"))

    from src.config import settings, get_config_status

    # 显示配置来源
    status = get_config_status()
    console.print(f"\n[bold]配置来源:[/bold] {settings.config_source}")
    console.print(f"[bold]配置文件:[/bold] {status['config_file']}")

    console.print(f"\n[bold]Gemini:[/bold]")
    console.print(f"  模型: {settings.gemini.model}")
    api_key_status = '✅ 已配置' if status['gemini']['api_key_configured'] else '❌ 未配置'
    console.print(f"  API Key: {api_key_status}")

    console.print(f"\n[bold]GitHub:[/bold]")
    token_status = '✅ 已配置' if status['github']['token_configured'] else '❌ 未配置'
    console.print(f"  Token: {token_status}")
    console.print(f"  最小 Stars: {settings.github.min_stars}")

    console.print(f"\n[bold]Twitter:[/bold]")
    console.print(f"  Cookies 路径: {settings.twitter.cookies_path}")
    cookies_status = '✅ 存在' if status['twitter']['cookies_exists'] else '❌ 不存在'
    console.print(f"  Cookies 文件: {cookies_status}")

    console.print(f"\n[bold]PushPlus:[/bold]")
    push_status = '✅ 已配置' if status['pushplus']['token_configured'] else '❌ 未配置'
    console.print(f"  Token: {push_status}")
    console.print(f"  启用推送: {'是' if settings.push.enabled else '否'}")

    console.print(f"\n[bold]公众号:[/bold]")
    console.print(f"  名称: {settings.account.name}")
    console.print(f"  领域: {settings.account.niche}")


@cli.command()
@click.option('--fix', '-f', is_flag=True, help='尝试自动修复配置问题')
def validate(fix):
    """✅ 验证配置文件"""
    console.print(Panel.fit("✅ 配置验证", style="bold cyan"))

    from src.utils.config_validator import ConfigValidator

    validator = ConfigValidator()
    result = validator.validate()
    validator.print_report(result)

    if result.passed:
        console.print("\n[bold green]🎉 配置验证通过！[/bold green]")
    else:
        console.print("\n[bold red]⚠️ 配置存在问题，请修复后再运行[/bold red]")


@cli.command()
@click.argument('content_file', type=click.Path(exists=True))
@click.option('--fix', '-f', is_flag=True, help='自动修复违禁词（替换 AI 痕迹词）')
@click.option('--output', '-o', default='', help='修复后输出到指定文件')
def check(content_file, fix, output):
    """🔍 检查文章违禁词"""
    console.print(Panel.fit("🔍 违禁词检查", style="bold cyan"))

    from pathlib import Path
    from src.utils.content_filter import ContentFilter
    from src.config import settings

    # 读取文件内容
    file_path = Path(content_file)
    content = file_path.read_text(encoding='utf-8')

    console.print(f"\n[bold]文件:[/bold] {file_path}")
    console.print(f"[bold]字数:[/bold] {len(content)}")

    # 初始化过滤器
    filter_instance = ContentFilter(
        banned_words=settings.content.banned_words,
        replacements=settings.content.ai_word_replacements,
    )

    if fix:
        cleaned_content, result = filter_instance.check_and_clean(content)
        filter_instance.print_report(result)

        if output:
            output_path = Path(output)
            output_path.write_text(cleaned_content, encoding='utf-8')
            console.print(f"\n[green]✅ 已修复并保存到: {output_path}[/green]")
        else:
            file_path.write_text(cleaned_content, encoding='utf-8')
            console.print(f"\n[green]✅ 已修复并覆盖原文件[/green]")

        console.print(f"[dim]替换了 {len(result.replaced_words)} 个 AI 痕迹词[/dim]")
    else:
        result = filter_instance.check(content)
        filter_instance.print_report(result)


@cli.command()
def clean():
    """🧹 清理检查点和缓存"""
    console.print(Panel.fit("🧹 清理缓存", style="bold cyan"))

    from src.factory.executor import WorkflowExecutor

    executor = WorkflowExecutor()
    executor.clear_checkpoints()
    console.print("[green]✅ 检查点已清除[/green]")


# ═══════════════════════════════════════════════════════════════════════════════
# 保留旧命令（向下兼容）
# ═══════════════════════════════════════════════════════════════════════════════

@cli.command(hidden=True)
def github():
    """[旧命令] 运行 GitHub 猎手"""
    console.print("[yellow]提示: 此命令已弃用，请使用 'hunter run -t github'[/yellow]\n")
    from src.intel.github_hunter import main
    main()


@cli.command(hidden=True)
def pain():
    """[旧命令] 运行痛点雷达"""
    console.print("[yellow]提示: 此命令已弃用，请使用 'hunter run -t pain'[/yellow]\n")
    from src.intel.pain_radar import main
    asyncio.run(main())


@cli.command(hidden=True)
def publish():
    """[旧命令] 运行全能猎手"""
    console.print("[yellow]提示: 此命令已弃用，请使用 'hunter run -t news'[/yellow]\n")
    from src.intel.auto_publisher import main
    asyncio.run(main())


@cli.command(hidden=True)
def refine():
    """[旧命令] 运行内容精炼器"""
    console.print("[yellow]提示: 此命令已弃用[/yellow]\n")
    from src.refiner.refiner import main
    main()


@cli.command(hidden=True)
@click.option('--niche', '-n', default='', help='细分领域')
@click.option('--trends', '-t', multiple=True, help='趋势关键词')
@click.option('--resume', '-r', default='', help='从指定 Skill 恢复')
def factory(niche, trends, resume):
    """[旧命令] 运行内容工厂"""
    console.print("[yellow]提示: 此命令已弃用，请使用 'hunter run'[/yellow]\n")
    from src.factory.executor import WorkflowExecutor

    executor = WorkflowExecutor()
    context = asyncio.run(executor.run(
        niche=niche,
        trends=list(trends) if trends else [],
        resume_from=resume if resume else None,
    ))


@cli.command(name='all', hidden=True)
def all_modules():
    """[旧命令] 全员出击"""
    console.print("[yellow]提示: 此命令已弃用，请使用 'hunter run'[/yellow]\n")


if __name__ == "__main__":
    cli()
