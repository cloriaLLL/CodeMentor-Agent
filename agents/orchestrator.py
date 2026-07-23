"""CodeMentor Agent MVP — Orchestrator Agent.

教学主控 Agent：对话驱动的自适应学习导师。
核心教学节拍：简述概括 → 环境准备 → 学习路径 → 分点详细讲解 → 代码实例 → 按需练习 → 实战/面试 → 生态总结。

设计原则：
- 不硬编码预设题目或学习节点，通过自然语言对话识别学习目标
- 所有 LLM 调用统一异步，使用原生多轮 messages 数组传递对话历史
- 每次讲解知识点必须非常详细、有深度、有代码示例
- 按用户需求动态生成练习题，不预设题目
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from pydantic import BaseModel, Field

from agents import load_prompt, load_seed_data
from agents.llm_client import (
    LLMCallError,
    LLMConfigError,
    LLMProvider,
    ZHIPU_MODELS,
    get_llm_provider_with_fallback,
)


class TeachContent(BaseModel):
    markdown_content: str = Field(..., description="Markdown 教学内容")
    grounding_source: str = Field(..., description="基准源名称")
    history_notes: str = Field(..., description="历史演进说明")
    next_actions: list[str] = Field(..., description="可选下一步动作")


class EcosystemContent(BaseModel):
    stack_summary: str = Field(..., description="工业栈总结")
    cross_language_equivalent: dict = Field(..., description="跨语言等价物")
    next_node_recommendation: str = Field(..., description="下一节点推荐")


class OrchestratorAgent:
    """对话驱动的自适应学习导师。"""

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self.seed_data = load_seed_data()
        self.llm = llm_provider or get_llm_provider_with_fallback()
        self._llm_enabled = self.llm.name != "mock"
        self.SYSTEM_PROMPT = load_prompt("mentor")

    def _build_messages(
        self,
        user_message: str,
        history: Optional[list[dict]] = None,
        parent_summary: Optional[str] = None,
        mode: str = "chat",
    ) -> list[dict]:
        """构建发送给LLM的完整messages数组（原生多轮格式）。

        system content 统一在此处组装：基础 mentor prompt +（笔记本模式时）
        notebook suffix prompt +（有父章节摘要时）笔记本背景上下文。
        这样无论 chat / chat_stream，messages[0] 始终携带完整指令。
        """
        system_content = self.SYSTEM_PROMPT
        if mode == "notebook":
            system_content += load_prompt("mentor_notebook_suffix")
        if parent_summary:
            system_content += (
                f"\n\n---\n\n## 笔记本背景上下文\n\n"
                f"以下是其他章节的学习总结，供你理解整体进度：\n\n{parent_summary}"
            )
        messages = [{"role": "system", "content": system_content}]
        if history:
            for m in history[-20:]:
                role = m.get("role", "")
                content = m.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(
        self,
        user_message: str,
        history: Optional[list[dict]] = None,
        mode: str = "chat",
        parent_summary: Optional[str] = None,
    ) -> str:
        """自由对话接口。mode='notebook' 时启用笔记整理模式。"""
        # messages 已含完整 system content（含笔记本 suffix / 父摘要），
        # llm_client 在 messages 非 None 时会忽略 system_prompt 参数，
        # 因此 notebook 模式指令必须通过 _build_messages 注入而非外层拼接。
        messages = self._build_messages(user_message, history, parent_summary, mode)
        try:
            return await self.llm.chat(
                system_prompt="",
                user_message=user_message,
                temperature=0.7,
                max_tokens=8192,
                messages=messages,
            )
        except (LLMCallError, LLMConfigError) as e:
            if self._llm_enabled:
                return (
                    f"LLM 调用遇到问题：{e}\n\n"
                    "请检查网络连接或 API Key 配置，也可以稍后重试。"
                )
            return self._mock_intro_reply(user_message)

    async def chat_stream(
        self,
        user_message: str,
        history: Optional[list[dict]] = None,
        mode: str = "chat",
        parent_summary: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """流式自由对话接口，逐token yield。mode='notebook'时启用笔记整理模式。"""
        messages = self._build_messages(user_message, history, parent_summary, mode)
        try:
            async for chunk in self.llm.chat_stream(
                system_prompt="",
                user_message=user_message,
                temperature=0.7,
                max_tokens=8192,
                messages=messages,
            ):
                yield chunk
        except (LLMCallError, LLMConfigError) as e:
            if self._llm_enabled:
                yield (
                    f"\n\nLLM 流式调用遇到问题：{e}\n\n"
                    "请检查网络连接或 API Key 配置，也可以稍后重试。"
                )
            else:
                yield self._mock_intro_reply(user_message)

    def _mock_intro_reply(self, user_message: str) -> str:
        if any(k in user_message for k in ["你好", "hello", "hi", "在吗"]):
            return (
                "## CodeMentor — 编程学习导师\n\n"
                "你好！我是 CodeMentor，可以带你系统学习各种编程技术。\n\n"
                "### 当前处于 Mock 模式\n\n"
                "请先配置 LLM Provider 以启用真实 AI 导师：\n\n"
                "**推荐：智谱 GLM-4-Flash（永久免费）**\n"
                "1. 到 https://bigmodel.cn 注册获取 API Key\n"
                "2. 在项目根目录 `.env` 文件中设置 `ZHIPU_API_KEY=你的key`\n"
                "3. 重启服务后即可开始学习\n\n"
                "配置完成后，你可以说「我要学习 Python」开始体验。"
            )
        return (
            "## Mock 模式\n\n"
            "当前未配置 LLM，无法进行教学对话。\n\n"
            "配置方法：在 `.env` 中设置 `ZHIPU_API_KEY` 启用智谱免费模型。"
        )

    # ---------- 旧 API 兼容方法 ---------- #

    def teach(self, node_id: str) -> TeachContent:
        for atom in self.seed_data.get("knowledge_atoms", []):
            if atom.get("node_id") == node_id:
                tc = atom.get("teach_content", {})
                return TeachContent(
                    markdown_content=tc.get("markdown_content", "请通过聊天框开始学习对话"),
                    grounding_source=atom.get("grounding_doc", {}).get("source_name", ""),
                    history_notes=atom.get("evolution_history", {}).get("key_changes", ""),
                    next_actions=tc.get("next_actions", ["通过对话框继续学习"]),
                )
        raise ValueError(f"Node not found: {node_id}")

    def ecosystem_summary(self, node_id: str) -> EcosystemContent:
        for atom in self.seed_data.get("knowledge_atoms", []):
            if atom.get("node_id") == node_id:
                eco = atom.get("ecosystem_mapping", {})
                return EcosystemContent(
                    stack_summary=eco.get("stack_summary", ""),
                    cross_language_equivalent=eco.get("cross_language_equivalents", {}),
                    next_node_recommendation=eco.get("next_node_recommendation", ""),
                )
        raise ValueError(f"Node not found: {node_id}")
