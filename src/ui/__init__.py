"""
Hunter AI 内容工厂 - 模块化 UI 包

目录结构：
- constants.py: 常量定义（SKILLS_INFO、CSS 加载）
- handlers.py: 业务处理函数
- app.py: 主应用组装
- components/: 公共组件（header、footer）
- tabs/: 各功能 Tab 模块
"""

from .app import create_app
from .constants import CUSTOM_CSS, SKILLS_INFO

__all__ = ["create_app", "CUSTOM_CSS", "SKILLS_INFO"]
