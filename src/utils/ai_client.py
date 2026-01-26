"""
Hunter AI 内容工厂 - 统一 AI 客户端

功能：
- 支持官方 Gemini API（google.genai SDK）
- 支持 OpenAI 兼容 API（第三方聚合服务）
- 支持 Imagen 图片生成 API
- 统一的调用接口，自动根据配置切换

使用方法：
    from src.utils.ai_client import get_ai_client, generate_content, generate_image

    # 方式一：获取客户端实例
    client = get_ai_client()
    response = await client.generate("你好")

    # 方式二：直接调用
    response = await generate_content("你好")

    # 方式三：生成图片
    image_path = await generate_image("一只可爱的猫咪", output_path="cat.png")
"""

import httpx
import base64
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from rich.console import Console

from src.config import get_settings

console = Console()

# AI 请求超时配置（秒）
AI_TIMEOUT = 300  # 5 分钟，生成长文章需要较长时间
AI_MAX_RETRIES = 3  # 最大重试次数


@dataclass
class AIResponse:
    """AI 响应结构"""
    text: str                          # 生成的文本
    model: str                         # 使用的模型
    usage: Optional[dict] = None       # Token 使用情况


@dataclass
class ImageResponse:
    """图片生成响应结构"""
    image_bytes: bytes                 # 图片二进制数据
    model: str                         # 使用的模型
    saved_path: Optional[str] = None   # 保存路径（如果已保存）


class BaseAIClient:
    """AI 客户端基类"""

    def __init__(self, settings):
        self.settings = settings
        self.model = settings.gemini.model

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """生成内容（子类实现）"""
        raise NotImplementedError


class OfficialGeminiClient(BaseAIClient):
    """官方 Gemini API 客户端"""

    def __init__(self, settings):
        super().__init__(settings)
        from google import genai
        self.client = genai.Client(api_key=settings.gemini.api_key)
        # 图片模型从配置读取（必须配置才能使用图片生成）
        self.image_model = settings.gemini.image_model

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """调用官方 Gemini API"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            **kwargs
        )
        return AIResponse(
            text=response.text,
            model=self.model,
            usage=None  # 官方 SDK 返回格式不同
        )

    def generate_sync(self, prompt: str, **kwargs) -> AIResponse:
        """同步调用官方 Gemini API"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            **kwargs
        )
        return AIResponse(
            text=response.text,
            model=self.model,
            usage=None
        )

    def generate_image_sync(self, prompt: str, output_path: Optional[str] = None, **kwargs) -> ImageResponse:
        """
        使用 Imagen 模型生成图片（同步）

        Args:
            prompt: 图片描述（英文效果更好）
            output_path: 保存路径（可选）
            **kwargs: 额外参数（number_of_images, aspect_ratio 等）

        Returns:
            ImageResponse: 图片响应
        """
        from google.genai import types

        config = types.GenerateImagesConfig(
            number_of_images=kwargs.get("number_of_images", 1),
            aspect_ratio=kwargs.get("aspect_ratio", "16:9"),  # 适合公众号封面
            safety_filter_level=kwargs.get("safety_filter_level", "BLOCK_MEDIUM_AND_ABOVE"),
        )

        response = self.client.models.generate_images(
            model=self.image_model,
            prompt=prompt,
            config=config,
        )

        # 获取第一张图片
        if response.generated_images:
            image_data = response.generated_images[0].image.image_bytes
            saved_path = None

            # 保存到文件
            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_bytes(image_data)
                saved_path = output_path

            return ImageResponse(
                image_bytes=image_data,
                model=self.image_model,
                saved_path=saved_path
            )
        else:
            raise RuntimeError("图片生成失败：未返回任何图片")


class OpenAICompatibleClient(BaseAIClient):
    """OpenAI 兼容 API 客户端（第三方聚合）"""

    def __init__(self, settings):
        super().__init__(settings)
        self.base_url = settings.gemini.base_url.rstrip('/')
        self.api_key = settings.gemini.api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # 图片模型从配置读取（必须配置才能使用图片生成）
        self.image_model = settings.gemini.image_model

    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """调用 OpenAI 兼容 API（异步，带重试）

        重试策略：
        - 429 速率限制：2/4/8 秒指数退避
        - 超时错误：10/20/30 秒递增等待
        """
        last_error = None

        for attempt in range(AI_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": kwargs.get("max_tokens", 4096),
                            "temperature": kwargs.get("temperature", 0.7),
                        }
                    )

                    # 429 速率限制：指数退避重试
                    if response.status_code == 429:
                        if attempt < AI_MAX_RETRIES - 1:
                            wait_time = 2 * (2 ** attempt)  # 2s, 4s, 8s
                            console.print(f"[yellow]⏳ 速率限制(429)，{wait_time}秒后重试 ({attempt + 1}/{AI_MAX_RETRIES})...[/yellow]")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()

                    response.raise_for_status()
                    data = response.json()

                    return AIResponse(
                        text=data["choices"][0]["message"]["content"],
                        model=self.model,
                        usage=data.get("usage")
                    )
            except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < AI_MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 10  # 递增等待：10s, 20s, 30s
                    console.print(f"[yellow]⏱️ AI 请求超时，{wait_time}秒后重试 ({attempt + 1}/{AI_MAX_RETRIES})...[/yellow]")
                    await asyncio.sleep(wait_time)
                else:
                    console.print(f"[red]❌ AI 请求超时，已重试 {AI_MAX_RETRIES} 次[/red]")
            except Exception as e:
                last_error = e
                if attempt < AI_MAX_RETRIES - 1:
                    console.print(f"[yellow]⚠️ AI 请求失败: {e}，重试中...[/yellow]")
                    await asyncio.sleep(5)
                else:
                    raise

        raise last_error or RuntimeError("AI 请求失败")

    def generate_sync(self, prompt: str, **kwargs) -> AIResponse:
        """调用 OpenAI 兼容 API（同步，带重试）

        重试策略：
        - 429 速率限制：2/4/8 秒指数退避
        - 超时错误：10/20/30 秒递增等待
        """
        import time
        last_error = None

        for attempt in range(AI_MAX_RETRIES):
            try:
                with httpx.Client(timeout=AI_TIMEOUT) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": kwargs.get("max_tokens", 4096),
                            "temperature": kwargs.get("temperature", 0.7),
                        }
                    )

                    # 429 速率限制：指数退避重试
                    if response.status_code == 429:
                        if attempt < AI_MAX_RETRIES - 1:
                            wait_time = 2 * (2 ** attempt)  # 2s, 4s, 8s
                            console.print(f"[yellow]⏳ 速率限制(429)，{wait_time}秒后重试 ({attempt + 1}/{AI_MAX_RETRIES})...[/yellow]")
                            time.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()

                    response.raise_for_status()
                    data = response.json()

                    return AIResponse(
                        text=data["choices"][0]["message"]["content"],
                        model=self.model,
                        usage=data.get("usage")
                    )
            except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                last_error = e
                if attempt < AI_MAX_RETRIES - 1:
                    wait_time = (attempt + 1) * 10
                    console.print(f"[yellow]⏱️ AI 请求超时，{wait_time}秒后重试 ({attempt + 1}/{AI_MAX_RETRIES})...[/yellow]")
                    time.sleep(wait_time)
                else:
                    console.print(f"[red]❌ AI 请求超时，已重试 {AI_MAX_RETRIES} 次[/red]")
            except Exception as e:
                last_error = e
                if attempt < AI_MAX_RETRIES - 1:
                    console.print(f"[yellow]⚠️ AI 请求失败: {e}，重试中...[/yellow]")
                    time.sleep(5)
                else:
                    raise

        raise last_error or RuntimeError("AI 请求失败")

    def generate_image_sync(self, prompt: str, output_path: Optional[str] = None, **kwargs) -> ImageResponse:
        """
        使用 OpenAI 兼容 API 生成图片（同步）

        通过 /images/generations 端点调用（OpenAI 标准接口）

        Args:
            prompt: 图片描述
            output_path: 保存路径（可选）
            **kwargs: 额外参数

        Returns:
            ImageResponse: 图片响应
        """
        with httpx.Client(timeout=AI_TIMEOUT) as client:
            response = client.post(
                f"{self.base_url}/images/generations",
                headers=self.headers,
                json={
                    "model": self.image_model,
                    "prompt": prompt,
                    "n": kwargs.get("n", 1),
                    "response_format": "b64_json",  # 返回 base64 编码
                }
            )
            response.raise_for_status()
            data = response.json()

            # 解码 base64 图片
            if data.get("data") and len(data["data"]) > 0:
                image_b64 = data["data"][0].get("b64_json")
                if image_b64:
                    image_data = base64.b64decode(image_b64)
                    saved_path = None

                    # 保存到文件
                    if output_path:
                        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                        Path(output_path).write_bytes(image_data)
                        saved_path = output_path

                    return ImageResponse(
                        image_bytes=image_data,
                        model=self.image_model,
                        saved_path=saved_path
                    )

            raise RuntimeError("图片生成失败：未返回有效数据")


# 存储客户端实例（手动管理缓存）
_ai_client_instance = None
_ai_client_provider = None


def get_ai_client() -> BaseAIClient:
    """
    获取 AI 客户端

    根据配置自动选择：
    - provider=official → 官方 Gemini API
    - provider=openai_compatible → OpenAI 兼容 API

    Returns:
        BaseAIClient: AI 客户端实例
    """
    global _ai_client_instance, _ai_client_provider

    settings = get_settings()
    current_provider = "openai_compatible" if settings.gemini.is_openai_compatible else "official"

    # 如果 provider 改变了，重新创建客户端
    if _ai_client_instance is None or _ai_client_provider != current_provider:
        if settings.gemini.is_openai_compatible:
            _ai_client_instance = OpenAICompatibleClient(settings)
        else:
            _ai_client_instance = OfficialGeminiClient(settings)
        _ai_client_provider = current_provider

    return _ai_client_instance


async def generate_content(prompt: str, **kwargs) -> str:
    """
    便捷方法：生成内容（异步）

    Args:
        prompt: 提示词
        **kwargs: 额外参数

    Returns:
        str: 生成的文本
    """
    client = get_ai_client()
    response = await client.generate(prompt, **kwargs)
    return response.text


def generate_content_sync(prompt: str, **kwargs) -> str:
    """
    便捷方法：生成内容（同步）

    Args:
        prompt: 提示词
        **kwargs: 额外参数

    Returns:
        str: 生成的文本
    """
    client = get_ai_client()
    response = client.generate_sync(prompt, **kwargs)
    return response.text


def generate_image(prompt: str, output_path: str, **kwargs) -> ImageResponse:
    """
    便捷方法：生成图片（同步）

    使用 Imagen 模型根据文本描述生成图片
    注意：第三方聚合 API 可能不支持图片生成，会自动降级

    Args:
        prompt: 图片描述（英文效果更好）
        output_path: 图片保存路径
        **kwargs: 额外参数
            - aspect_ratio: 宽高比（"16:9", "1:1", "4:3" 等）
            - number_of_images: 生成数量（默认 1）

    Returns:
        ImageResponse: 图片响应（包含 image_bytes 和 saved_path）

    Example:
        >>> response = generate_image(
        ...     "A futuristic AI robot coding on laptop",
        ...     "output/covers/robot.png",
        ...     aspect_ratio="16:9"
        ... )
        >>> print(f"图片已保存到: {response.saved_path}")
    """
    client = get_ai_client()
    try:
        return client.generate_image_sync(prompt, output_path, **kwargs)
    except Exception as e:
        # 图片生成失败时的处理
        raise RuntimeError(f"图片生成失败: {e}")


def generate_project_cover(
    project_name: str,
    project_desc: str,
    output_path: str,
    style: str = "tech"
) -> ImageResponse:
    """
    为 GitHub 项目生成封面图

    根据项目信息自动构建英文 prompt，生成适合公众号的封面图

    Args:
        project_name: 项目名称
        project_desc: 项目描述
        output_path: 保存路径
        style: 风格（tech=科技感, minimal=简约, vibrant=活力）

    Returns:
        ImageResponse: 图片响应
    """
    # 风格映射
    style_prompts = {
        "tech": "futuristic technology style, dark blue gradient background, glowing neon accents, clean modern design",
        "minimal": "minimalist design, clean white background, subtle shadows, professional look",
        "vibrant": "colorful gradient background, energetic and dynamic, modern flat design",
    }

    style_desc = style_prompts.get(style, style_prompts["tech"])

    # 构建英文 prompt
    prompt = f"""Create a professional cover image for a GitHub open source project.

Project: {project_name}
Description: {project_desc}

Style requirements:
- {style_desc}
- Include abstract tech elements (code symbols, nodes, connections)
- Text-free design (no text or letters in the image)
- Suitable for WeChat article cover (16:9 aspect ratio)
- High quality, visually appealing
- Professional and trustworthy appearance
"""

    return generate_image(prompt, output_path, aspect_ratio="16:9")


# 导出
__all__ = [
    "AIResponse",
    "ImageResponse",
    "BaseAIClient",
    "OfficialGeminiClient",
    "OpenAICompatibleClient",
    "get_ai_client",
    "generate_content",
    "generate_content_sync",
    "generate_image",
    "generate_project_cover",
]
