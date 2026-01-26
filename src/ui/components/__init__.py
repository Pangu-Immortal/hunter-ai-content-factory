"""
Hunter AI 内容工厂 - 公共组件

包含可复用的 UI 组件：
- create_header: 顶部标题
- create_footer: 底部页脚
"""

from .footer import create_footer
from .header import create_header

__all__ = ["create_header", "create_footer"]
