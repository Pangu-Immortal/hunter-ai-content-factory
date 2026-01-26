"""
Hunter AI 内容工厂 - Tabs 模块

包含所有功能 Tab 的构建函数：
- create_github_tab: GitHub 爆款
- create_pain_tab: 痛点诊断
- create_news_tab: 热点快报
- create_xhs_tab: 小红书种草
- create_auto_tab: 全自动生产
- create_check_tab: 内容审核
- create_settings_tab: 设置
- create_intro_tabs: 下部介绍区
"""

from .auto_tab import create_auto_tab
from .check_tab import create_check_tab
from .github_tab import create_github_tab
from .intro_tabs import create_intro_tabs
from .news_tab import create_news_tab
from .pain_tab import create_pain_tab
from .settings_tab import create_settings_tab
from .xhs_tab import create_xhs_tab

__all__ = [
    "create_github_tab",
    "create_pain_tab",
    "create_news_tab",
    "create_xhs_tab",
    "create_auto_tab",
    "create_check_tab",
    "create_settings_tab",
    "create_intro_tabs",
]
