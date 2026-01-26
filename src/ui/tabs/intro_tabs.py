"""
摆渡人AI系统 - 介绍 Tab（下部介绍区）

包含首页介绍和 6 个 Skill 详细说明
"""

import gradio as gr

from ..constants import SKILLS_INFO, get_image_path


def create_intro_tabs():
    """创建下部介绍区 Tabs（首页 + 6 个 Skill 介绍）"""

    gr.Markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: var(--brand-primary, #e91e63);">📚 6-Skill 工作流介绍</h2>
        <p style="color: var(--text-muted, #666);">像流水线一样高效协作，从选题到发布一气呵成</p>
    </div>
    """)

    with gr.Tabs() as bottom_tabs:
        # Tab: 首页介绍
        with gr.Tab("🏠 首页", id="home"):
            with gr.Row():
                with gr.Column(scale=1):
                    # 显示主图 - 无边框
                    main_img = get_image_path("hunter_intro_03.png")
                    if main_img:
                        gr.Image(main_img, label=None, show_label=False, height=300, container=False)
                with gr.Column(scale=2):
                    gr.Markdown("""
### 🦅 摆渡人AI系统

基于 **6-Skill 架构** 的智能内容生产系统。

#### 核心特点
| 特性 | 说明 |
|------|------|
| 🧩 **模块化** | 每个 Skill 独立运行，可单独调试 |
| 📍 **可追溯** | 每一步都有明确的输入输出 |
| 🔄 **可恢复** | 支持断点续作 |
| 🚫 **去 AI 化** | 内置违禁词检查，自动清理 AI 痕迹 |

#### 工作流程
```
选题 → 研究 → 结构 → 写作 → 封装 → 发布
```
                    """)

        # 6 个 Skill Tab
        for skill in SKILLS_INFO:
            with gr.Tab(f"{skill['emoji']} {skill['name']}", id=skill["id"]):
                with gr.Row():
                    with gr.Column(scale=1):
                        img_path = get_image_path(skill["image"])
                        if img_path:
                            gr.Image(img_path, label=None, show_label=False, height=250, container=False)
                        else:
                            gr.HTML(f"""
                            <div style="height: 250px; display: flex; align-items: center; justify-content: center;
                                background: linear-gradient(135deg, {skill["color"]}22, {skill["color"]}44);
                                border-radius: 16px; font-size: 5em;">
                                {skill["emoji"]}
                            </div>
                            """)

                    with gr.Column(scale=2):
                        gr.Markdown(
                            f"""
### {skill["emoji"]} {skill["name"]}

**{skill["subtitle"]}**

{skill["description"]}

#### 输出内容
| 输出项 | 说明 |
|--------|------|
"""
                            + "\n".join([f"| {out} | 由 AI 自动生成 |" for out in skill["outputs"]])
                        )

    return bottom_tabs
