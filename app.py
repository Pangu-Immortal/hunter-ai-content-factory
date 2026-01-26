"""
Hunter AI 内容工厂 - Hugging Face Spaces 入口

此文件用于 Hugging Face Spaces 部署
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置环境变量
os.environ["NO_PROXY"] = "localhost,127.0.0.1,0.0.0.0"
os.environ["no_proxy"] = "localhost,127.0.0.1,0.0.0.0"

# 导入 Gradio 应用
from src.ui import create_app

# 创建 Gradio 应用
demo = create_app()

# Hugging Face Spaces 入口
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # HF Spaces 自动提供公网访问
        show_error=True,
    )
