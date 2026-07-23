"""CodeMentor Agent — LLM Provider 抽象层 (Session 5 + Session 6 + 现代化异步).

统一封装多 LLM Provider，支持：
1. ZHIPU (智谱 GLM-4 系列) — 默认，OpenAI 兼容接口，永久免费无 Token 上限
2. OLLAMA (本地 Ollama) — OpenAI 兼容接口，完全离线
3. MOCK — 兜底模式，返回预置提示，保证 Demo 不崩

通过环境变量切换：
- LLM_PROVIDER: 显式指定 (zhipu/ollama/mock)
- ZHIPU_API_KEY: 智谱 API Key
- ZHIPU_MODEL: 智谱模型名 (默认 glm-4-flash，见下方 ZHIPU_MODELS 常量)
- OLLAMA_HOST: Ollama 服务地址 (默认 http://localhost:11434)
- OLLAMA_MODEL: Ollama 模型名 (默认 qwen2.5:7b)

实现依据：DOC-03 §4 LLM 接入层契约
现代化升级：使用 AsyncOpenAI 原生异步客户端，删除 asyncio.to_thread/queue 复杂包装，
           支持真正的流式 SSE 输出，与 FastAPI EventSourceResponse 无缝集成。
"""
from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

# LLM 调用超时（秒），防止网络请求卡死
LLM_TIMEOUT = 30


# --------------------------------------------------------------------------- #
# 智谱 GLM 免费模型列表
# --------------------------------------------------------------------------- #

ZHIPU_MODELS = {
    "glm-4-flash": {
        "name": "GLM-4-Flash",
        "description": "基础免费模型，适合日常对话和教学",
        "max_tokens": 131072,
        "free": True,
    },
    "glm-4-6v-flash": {
        "name": "GLM-4.6V-Flash",
        "description": "支持多模态，理解图表和图片内容",
        "max_tokens": 131072,
        "free": True,
    },
    "glm-4-7-flash": {
        "name": "GLM-4.7-Flash",
        "description": "7B 参数模型，平衡性能与速度",
        "max_tokens": 131072,
        "free": True,
    },
    "glm-4v-flash": {
        "name": "GLM-4V-Flash",
        "description": "视觉理解模型，分析图像内容",
        "max_tokens": 131072,
        "free": True,
    },
}
"""智谱免费模型配置常量（仅对话/多模态模型，已剔除图像/视频生成模型）。

在 .env 中设置 ZHIPU_MODEL 选择模型，例如：
  ZHIPU_MODEL=glm-4-6v-flash  # 启用多模态模型
  ZHIPU_MODEL=glm-4-1v-thinking-flash  # 启用思考链模型
"""

DEFAULT_ZHIPU_MODEL = "glm-4-flash"


# --------------------------------------------------------------------------- #
# 异常定义
# --------------------------------------------------------------------------- #

class LLMError(Exception):
    """LLM 调用基础异常"""


class LLMConfigError(LLMError):
    """LLM 配置错误（如未设置 API Key）。

    携带 can_fallback 标志，告知上层是否可降级到 Mock 模式。
    """

    def __init__(self, message: str, can_fallback: bool = True) -> None:
        super().__init__(message)
        self.can_fallback = can_fallback


class LLMCallError(LLMError):
    """LLM 调用失败（网络/超时/模型错误）"""

    def __init__(self, message: str, provider: str, can_fallback: bool = True) -> None:
        super().__init__(message)
        self.provider = provider
        self.can_fallback = can_fallback


# --------------------------------------------------------------------------- #
# Provider 抽象基类
# --------------------------------------------------------------------------- #

class LLMProvider(ABC):
    """LLM Provider 抽象基类（统一异步接口，避免阻塞事件循环）。"""

    name: str = "abstract"

    @abstractmethod
    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.7,
                   max_tokens: int = 2048, messages: Optional[list[dict]] = None) -> str:
        """异步调用 LLM，返回完整响应文本。

        :param messages: 可选的完整消息列表（含system），若提供则覆盖 system_prompt+user_message
        """

    async def chat_stream(self, system_prompt: str, user_message: str,
                          temperature: float = 0.7, max_tokens: int = 2048,
                          messages: Optional[list[dict]] = None) -> AsyncIterator[str]:
        """流式调用 LLM，逐 chunk 返回。

        默认实现：调用 chat 后一次性 yield。子类可重写以实现真正的流式。
        """
        yield await self.chat(system_prompt, user_message, temperature, max_tokens, messages)


# --------------------------------------------------------------------------- #
# OpenAI 兼容 Provider 基类（智谱、Ollama 共用）
# --------------------------------------------------------------------------- #

class _OpenAICompatibleProvider(LLMProvider):
    """OpenAI SDK 兼容的 Provider 基类（现代化异步版本）。

    使用 AsyncOpenAI 原生异步客户端，直接 await 调用，
    无需 asyncio.to_thread 线程池包装，性能更优且支持真正的流式 SSE。
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        # 延迟导入，避免未安装 openai 时影响 Mock 模式
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise LLMConfigError(
                f"openai SDK 未安装，请运行：pip install openai。原因：{e}",
                can_fallback=True,
            ) from e
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=LLM_TIMEOUT,
        )
        self.model = model

    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.7,
                   max_tokens: int = 4096, messages: Optional[list[dict]] = None) -> str:
        """原生异步调用 LLM，返回完整响应文本。

        :param messages: 可选的完整消息列表（含system），若提供则覆盖 system_prompt+user_message
        """
        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
                timeout=LLM_TIMEOUT + 30,
            )
            return response.choices[0].message.content or ""
        except asyncio.TimeoutError as e:
            raise LLMCallError(
                f"{self.name} 调用超时（{LLM_TIMEOUT + 30}秒），请检查网络或稍后重试",
                provider=self.name,
                can_fallback=True,
            ) from e
        except LLMCallError:
            raise
        except Exception as e:
            raise LLMCallError(
                f"{self.name} 调用失败：{type(e).__name__}: {e}",
                provider=self.name,
                can_fallback=True,
            ) from e

    async def chat_stream(self, system_prompt: str, user_message: str,
                          temperature: float = 0.7, max_tokens: int = 4096,
                          messages: Optional[list[dict]] = None) -> AsyncIterator[str]:
        """真正的异步流式调用，逐 token yield。

        :param messages: 可选的完整消息列表（含system），若提供则覆盖 system_prompt+user_message
        """
        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
        except Exception as e:
            raise LLMCallError(
                f"{self.name} 流式调用失败：{type(e).__name__}: {e}",
                provider=self.name,
                can_fallback=True,
            ) from e


# --------------------------------------------------------------------------- #
# 智谱 GLM Provider
# --------------------------------------------------------------------------- #

class ZhipuProvider(_OpenAICompatibleProvider):
    """智谱 GLM-4 系列 Provider（永久免费，无 Token 上限）。

    官方文档：https://open.bigmodel.cn/dev/api
    OpenAI 兼容接口 base_url：https://open.bigmodel.cn/api/paas/v4/

    支持的免费对话/多模态模型（通过 ZHIPU_MODEL 环境变量选择）：
    - glm-4-flash: 基础模型，适合日常对话和教学
    - glm-4-6v-flash: 多模态模型，理解图表和图片
    - glm-4-7-flash: 7B 参数模型，平衡性能与速度
    - glm-4-1v-thinking-flash: 支持思考链，适合逻辑推理
    - glm-4v-flash: 视觉理解模型
    """

    name = "zhipu"

    def __init__(self, api_key: str, model: str = DEFAULT_ZHIPU_MODEL) -> None:
        # 验证模型名称
        if model in ZHIPU_MODELS:
            model_name = model
        else:
            # 兼容智谱控制台显示的模型名（如 "GLM-4.6V-Flash" -> "glm-4-6v-flash"）
            normalized = model.lower().replace(".", "-").replace(" ", "-")
            model_name = normalized if normalized in ZHIPU_MODELS else DEFAULT_ZHIPU_MODEL

        super().__init__(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            model=model_name,
        )
        # 保存模型配置信息
        self.model_info = ZHIPU_MODELS.get(model_name, {})


# --------------------------------------------------------------------------- #
# Ollama Provider
# --------------------------------------------------------------------------- #

class OllamaProvider(_OpenAICompatibleProvider):
    """本地 Ollama Provider。

    需先安装 Ollama 并拉取模型：
        winget install Ollama.Ollama
        ollama pull qwen2.5:7b
    """

    name = "ollama"

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:7b") -> None:
        super().__init__(
            api_key="ollama",  # Ollama 不需要真实 key，但 SDK 要求非空
            base_url=f"{host}/v1",
            model=model,
        )


# --------------------------------------------------------------------------- #
# Mock Provider（兜底模式）
# --------------------------------------------------------------------------- #

class MockProvider(LLMProvider):
    """Mock Provider — 未配置 LLM 时的兜底模式。

    返回明确的提示信息，告知用户未启用真实 LLM。
    """

    name = "mock"

    def _build_mock_reply(self, user_message: str) -> str:
        return (
            "## [Mock 模式] LLM 未启用\n\n"
            "当前未配置 LLM Provider，返回的是预置提示文本。\n\n"
            "### 启用真实 LLM 的方式\n\n"
            "1. **智谱 GLM-4-Flash**（推荐）：\n"
            "   - 注册 https://bigmodel.cn 获取 API Key\n"
            "   - 在 `.env` 中设置 `ZHIPU_API_KEY=你的key`\n\n"
            "2. **Ollama 本地**：\n"
            "   - 安装：`winget install Ollama.Ollama`\n"
            "   - 拉模型：`ollama pull qwen2.5:7b`\n"
            "   - 在 `.env` 中设置 `LLM_PROVIDER=ollama`\n\n"
            "3. **显式 Mock**：\n"
            "   - 在 `.env` 中设置 `LLM_PROVIDER=mock`\n\n"
            "### 你刚才的输入\n\n"
            f"```\n{user_message[:500]}\n```"
        )

    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.7,
                   max_tokens: int = 4096, messages: Optional[list[dict]] = None) -> str:
        if messages:
            last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), user_message)
            return self._build_mock_reply(last_user)
        return self._build_mock_reply(user_message)


# --------------------------------------------------------------------------- #
# Provider 工厂
# --------------------------------------------------------------------------- #

def get_llm_provider(force_provider: Optional[str] = None) -> LLMProvider:
    """根据环境变量返回 LLM Provider 实例。

    :param force_provider: 强制指定 provider (zhipu/ollama/mock)，覆盖环境变量
    :return: LLMProvider 实例
    :raises LLMConfigError: 配置错误且不允许降级时抛出

    优先级：
    1. force_provider 参数
    2. LLM_PROVIDER 环境变量
    3. ZHIPU_API_KEY 已设置 → 智谱
    4. OLLAMA_HOST 已设置 → Ollama
    5. 默认 Mock
    """
    provider_name = (
        force_provider
        or os.getenv("LLM_PROVIDER")
        or ("zhipu" if os.getenv("ZHIPU_API_KEY") else None)
        or ("ollama" if os.getenv("OLLAMA_HOST") else None)
        or "mock"
    )

    if provider_name == "zhipu":
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise LLMConfigError(
                "已选择智谱 Provider，但未设置 ZHIPU_API_KEY 环境变量。"
                "请在 .env 文件中配置，或改用 Ollama/Mock 模式。",
                can_fallback=True,
            )
        model = os.getenv("ZHIPU_MODEL", DEFAULT_ZHIPU_MODEL)
        return ZhipuProvider(api_key=api_key, model=model)

    if provider_name == "ollama":
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        return OllamaProvider(host=host, model=model)

    if provider_name == "mock":
        return MockProvider()

    raise LLMConfigError(
        f"未知 LLM_PROVIDER 值：{provider_name}。支持：zhipu/ollama/mock",
        can_fallback=True,
    )


def get_llm_provider_with_fallback() -> LLMProvider:
    """获取 Provider，配置错误时自动降级到 Mock。

    用于后台 Agent 任务（Teach/Generator），保证 Demo 不崩。
    """
    try:
        return get_llm_provider()
    except LLMConfigError:
        return MockProvider()
