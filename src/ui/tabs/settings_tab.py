"""
摆渡人AI系统 - 设置 Tab

配置 API、推送、平台等所有设置项
"""

import gradio as gr
from ..handlers import get_config_info, load_current_config, save_config


def create_settings_tab():
    """创建设置 Tab"""
    with gr.Tab("⚙️ 设置", id="settings"):
        current_config = load_current_config()

        gr.Markdown("""
        ### 📋 配置说明
        所有配置修改后点击「保存配置」生效。敏感信息（API Key、Token、Cookie）请妥善保管。
        """)

        with gr.Row():
            # 左侧：配置表单
            with gr.Column(scale=3):

                # 🤖 Gemini AI 配置
                with gr.Accordion("🤖 Gemini AI 配置（必填）", open=True):
                    gr.Markdown("""
                    ---
                    **获取步骤：**

                    **方式一：官方 Gemini API（需翻墙，有免费额度）**
                    1. 打开 [Google AI Studio](https://aistudio.google.com/apikey)
                    2. 登录 Google 账号
                    3. 点击「Create API Key」创建密钥
                    4. 复制生成的 API Key
                    5. 下方「API 提供商」选择 `official`

                    **方式二：第三方聚合 API（推荐国内用户）**
                    1. 打开 [PackyAPI](https://www.packyapi.com) 或其他聚合平台
                    2. 注册并登录
                    3. 进入「API Keys」页面创建密钥
                    4. 复制 API Key 和 Base URL
                    5. 下方「API 提供商」选择 `openai_compatible`
                    ---
                    """)
                    gemini_provider = gr.Radio(
                        label="API 提供商",
                        choices=["official", "openai_compatible"],
                        value=current_config['gemini_provider'],
                        info="official=官方 Gemini（需翻墙）| openai_compatible=第三方聚合（国内可用）"
                    )
                    gemini_base_url = gr.Textbox(
                        label="API 地址（仅第三方需要）",
                        placeholder="https://www.packyapi.com/v1",
                        value=current_config['gemini_base_url'],
                        info="第三方聚合服务地址，官方 API 留空"
                    )
                    gemini_api_key = gr.Textbox(
                        label="API Key",
                        value=current_config['gemini_api_key'],
                        type="password",
                        info="从上述平台获取的密钥"
                    )
                    with gr.Row():
                        gemini_model = gr.Dropdown(
                            label="文本模型",
                            choices=[
                                "gemini-2.0-flash", "gemini-1.5-pro",
                                "gemini-3-pro-preview", "gemini-3-flash-preview",
                                "gemini-2.5-pro", "gemini-2.5-flash",
                            ],
                            value=current_config['gemini_model'],
                            allow_custom_value=True,
                            info="推荐: gemini-3-pro-preview（最强）或 gemini-2.0-flash（快速）"
                        )
                        gemini_image_model = gr.Dropdown(
                            label="图片模型（可选）",
                            choices=[
                                "", "imagen-3.0-generate-001",
                                "gemini-3-pro-image-preview",
                                "gemini-3-pro-image-preview-16-9-4K",
                            ],
                            value=current_config['gemini_image_model'],
                            allow_custom_value=True,
                            info="用于生成封面图，留空则使用在线服务"
                        )

                # 📮 PushPlus 微信推送配置
                with gr.Accordion("📮 PushPlus 微信推送配置", open=False):
                    gr.Markdown("""
                    ---
                    **获取步骤：**
                    1. 打开 [PushPlus 官网](https://www.pushplus.plus/)
                    2. 使用**微信扫码**登录
                    3. 进入「个人中心」
                    4. 复制页面上显示的 **Token**
                    5. **重要**：必须关注「pushplus推送加」公众号才能收到消息！

                    **免费额度**：每天 200 条消息
                    ---
                    """)
                    push_token = gr.Textbox(
                        label="PushPlus Token",
                        value=current_config['push_token'],
                        type="password",
                        info="从 pushplus.plus 个人中心获取"
                    )
                    push_enabled = gr.Checkbox(
                        label="启用推送",
                        value=current_config['push_enabled'],
                        info="关闭则只生成文章不推送到微信"
                    )

                # 🐦 Twitter/X 配置
                with gr.Accordion("🐦 Twitter/X 配置（痛点雷达需要）", open=False):
                    gr.Markdown("""
                    ---
                    **获取步骤：**
                    1. 用 Chrome 浏览器登录 [Twitter/X](https://x.com)
                    2. 安装浏览器扩展「**Cookie-Editor**」或「**EditThisCookie**」
                       - [Cookie-Editor 下载](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
                    3. 在 Twitter 页面点击扩展图标
                    4. 点击「**Export**」→「**Export as JSON**」
                    5. 将导出的 JSON 内容保存到项目的 `data/cookies.json` 文件

                    **注意**：Cookie 会过期（约7-14天），采集失败时需重新导出
                    ---
                    """)
                    twitter_cookies_path = gr.Textbox(
                        label="Cookies 文件路径",
                        value=current_config['twitter_cookies_path'],
                        info="相对于项目根目录，默认: data/cookies.json"
                    )

                # 📕 小红书配置
                with gr.Accordion("📕 小红书配置（小红书采集需要）", open=False):
                    gr.Markdown("""
                    ---
                    **Cookie 获取步骤（推荐方式）：**
                    1. 用 Chrome 浏览器登录 [小红书](https://www.xiaohongshu.com)
                    2. 按 `F12` 打开开发者工具
                    3. 切换到「**Console（控制台）**」标签
                    4. **首次使用需解除粘贴限制**：
                       - Chrome 默认禁止在控制台粘贴代码
                       - 先输入 `allow pasting` 然后按回车
                       - 看到提示后，即可正常粘贴
                    5. 输入以下命令并按回车：
                    ```
                    document.cookie
                    ```
                    6. 复制输出的**整个字符串**到下方「Cookie」输入框

                    **备选方式（获取更多 Cookie）：**
                    1. F12 → Application → Cookies → xiaohongshu.com
                    2. 手动复制所有 Cookie（重点需要 `web_session` 和 `a1`）
                    3. 格式: `a1=xxx; web_session=xxx; ...`

                    **注意**：Cookie 有效期约 7 天，过期后需重新获取
                    ---
                    """)
                    xhs_cookies = gr.Textbox(
                        label="Cookie 字符串",
                        value=current_config['xhs_cookies'],
                        lines=3,
                        info="从浏览器控制台获取的完整 Cookie"
                    )
                    with gr.Row():
                        xhs_default_keyword = gr.Textbox(
                            label="默认搜索关键词",
                            value=current_config['xhs_default_keyword'],
                            info="采集时的默认搜索词"
                        )
                        xhs_default_style = gr.Dropdown(
                            label="默认文章风格",
                            choices=["种草", "测评", "盘点"],
                            value=current_config['xhs_default_style'],
                            info="生成文章的默认风格"
                        )

                # 🐙 GitHub 配置
                with gr.Accordion("🐙 GitHub 配置（可选，提高 API 限额）", open=False):
                    gr.Markdown("""
                    ---
                    **获取步骤：**
                    1. 登录 [GitHub](https://github.com)
                    2. 点击右上角头像 → Settings
                    3. 左侧菜单最下方点击「**Developer settings**」
                    4. 点击「**Personal access tokens**」→「**Tokens (classic)**」
                    5. 点击「**Generate new token**」→「**Generate new token (classic)**」
                    6. Note 填写：`Hunter AI`
                    7. Expiration 选择有效期（建议 90 天或无期限）
                    8. 勾选 `public_repo` 权限
                    9. 点击「**Generate token**」
                    10. **立即复制** Token（只显示一次！）

                    **不配置也能用**，但 API 限额较低（每小时 60 次）
                    配置后可提升到每小时 **5000 次**
                    ---
                    """)
                    github_token = gr.Textbox(
                        label="GitHub Token",
                        value=current_config['github_token'],
                        type="password",
                        info="Personal Access Token，可选但推荐配置"
                    )
                    with gr.Row():
                        github_min_stars = gr.Slider(
                            label="最小 Stars 数",
                            minimum=50, maximum=5000,
                            value=current_config['github_min_stars'],
                            step=50,
                            info="只搜索 Star 数大于此值的项目"
                        )
                        github_days_since_update = gr.Slider(
                            label="更新时间过滤（天）",
                            minimum=7, maximum=365,
                            value=current_config['github_days_since_update'],
                            step=7,
                            info="只搜索最近 N 天内有更新的项目"
                        )

                # 📝 公众号设置
                with gr.Accordion("📝 公众号设置", open=False):
                    gr.Markdown("""
                    ---
                    配置你的公众号信息，AI 会根据这些设置调整写作风格和内容方向。
                    ---
                    """)
                    account_name = gr.Textbox(
                        label="公众号名称",
                        value=current_config['account_name'],
                        info="用于生成文章时的署名和风格参考"
                    )
                    account_niche = gr.Textbox(
                        label="细分领域",
                        value=current_config['account_niche'],
                        info="如: AI技术、职场成长、产品设计"
                    )
                    account_tone = gr.Textbox(
                        label="写作风格",
                        value=current_config['account_tone'],
                        info="如: 专业且引人入胜、轻松幽默、深度严谨"
                    )
                    with gr.Row():
                        min_length = gr.Number(
                            label="最小字数",
                            value=current_config['min_length'],
                            info="文章最少字数"
                        )
                        max_length = gr.Number(
                            label="最大字数",
                            value=current_config['max_length'],
                            info="文章最多字数"
                        )
                        max_title_length = gr.Number(
                            label="标题最大长度",
                            value=current_config['max_title_length'],
                            info="微信公众号建议不超过22字"
                        )

                # 💾 存储与系统配置
                with gr.Accordion("💾 存储与系统配置", open=False):
                    gr.Markdown("""
                    ---
                    高级配置，一般无需修改。
                    ---
                    """)
                    with gr.Row():
                        chromadb_path = gr.Textbox(
                            label="向量数据库路径",
                            value=current_config['chromadb_path'],
                            info="ChromaDB 存储路径，用于内容去重"
                        )
                        output_dir = gr.Textbox(
                            label="输出目录",
                            value=current_config['output_dir'],
                            info="生成文章的保存目录"
                        )
                    log_level = gr.Dropdown(
                        label="日志级别",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        value=current_config['log_level'],
                        info="DEBUG最详细，INFO正常，WARNING只显示警告"
                    )

            # 右侧：状态显示
            with gr.Column(scale=1):
                gr.Markdown("### 📊 当前配置状态")
                config_status = gr.Markdown(value=get_config_info())

                save_btn = gr.Button("💾 保存配置", variant="primary", size="lg")
                save_output = gr.Markdown()

                refresh_btn = gr.Button("🔄 刷新状态", variant="secondary")

                gr.Markdown("""
                ---
                ### 💡 配置优先级
                1. 界面设置 > config.yaml
                2. 保存后立即生效
                3. 部分设置需重启

                ### 🔒 安全提示
                - API Key 等敏感信息已加密存储
                - config.yaml 已加入 .gitignore
                - 不会被提交到 Git 仓库
                """)

        save_btn.click(
            fn=save_config,
            inputs=[
                gemini_provider, gemini_base_url, gemini_api_key, gemini_model, gemini_image_model,
                github_token, github_min_stars, github_days_since_update,
                push_token, push_enabled,
                twitter_cookies_path,
                xhs_cookies, xhs_default_keyword, xhs_default_style,
                account_name, account_niche, account_tone, min_length, max_length, max_title_length,
                chromadb_path, output_dir, log_level
            ],
            outputs=[save_output]
        )
        refresh_btn.click(fn=get_config_info, outputs=[config_status])
