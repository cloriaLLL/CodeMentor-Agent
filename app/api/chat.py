"""Chat endpoints - free conversation with SSE streaming support."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from agents.llm_client import LLMCallError, LLMConfigError
from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.schemas import ChatRequest, ChatResponse

router = APIRouter()

_HEARTBEAT_INTERVAL = 10.0


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> ChatResponse:
    """Free conversation endpoint (non-streaming, returns complete response)."""
    orchestrator = container.orchestrator
    conv_store = container.conversation_store

    history = req.history
    parent_summary: Optional[str] = None
    conv = None

    # Load history from store if conversation_id provided
    if req.conversation_id:
        conv_type = "notebook_chapter" if req.mode == "notebook" else "chat"
        conv = conv_store.get_or_create(
            conversation_id=req.conversation_id,
            type=conv_type,
            parent_id=req.parent_conversation_id,
        )
        history = conv_store.get_messages_as_llm_history(req.conversation_id, limit=20)
        if conv.parent_id:
            parent_summary = conv_store.get_parent_summary(conv.parent_id) or None

    try:
        reply = await orchestrator.chat(
            req.message, history, mode=req.mode, parent_summary=parent_summary
        )
        provider_name = orchestrator.llm.name

        # Persist messages after successful response
        if conv and reply.strip():
            conv_store.add_message(conv.conversation_id, role="user", content=req.message)
            conv_store.add_message(conv.conversation_id, role="assistant", content=reply)
            # Refresh parent summary for notebook chapters
            if conv.parent_id and conv_store.should_refresh_summary(conv.parent_id):
                try:
                    conv_store.refresh_parent_summary(conv.parent_id, orchestrator.llm)
                except Exception:
                    pass  # Summary refresh failure should not break chat

        return ChatResponse(
            status="success",
            reply=reply,
            provider=provider_name,
            degraded=(provider_name == "mock"),
        )
    except LLMConfigError as e:
        return ChatResponse(
            status="fallback",
            reply=(
                f"## LLM 配置错误\n\n"
                f"**原因**：{e}\n\n"
                f"**降级选项**：\n"
                f"1. 在 `.env` 中设置 `ZHIPU_API_KEY` 启用智谱 GLM-4-Flash\n"
                f"2. 安装 Ollama 本地服务并设置 `LLM_PROVIDER=ollama`\n"
                f"3. 设置 `LLM_PROVIDER=mock` 显式使用 Mock 模式\n\n"
                f"当前已自动降级到 Mock 模式，可继续使用 Demo。"
            ),
            provider="mock",
            degraded=True,
        )
    except LLMCallError as e:
        return ChatResponse(
            status="fallback",
            reply=(
                f"## LLM 调用失败\n\n"
                f"**Provider**：{e.provider}\n"
                f"**原因**：{e}\n\n"
                f"**建议**：\n"
                f"- 检查网络连接\n"
                f"- 检查 API Key 是否有效\n"
                f"- 切换 Provider：在 `.env` 中设置 `LLM_PROVIDER=ollama` 或 `mock`"
            ),
            provider=e.provider,
            degraded=True,
        )


@router.post("/chat_stream")
async def chat_stream(
    req: ChatRequest,
    container: AppContainer = Depends(get_container_from_request),
):
    """SSE streaming chat endpoint - real-time token-by-token response.

    SSE Protocol:
        event: start\n data: {"status": "connecting"}\n\n
        data: {"token": "..."}\n\n
        data: {"done": true}\n\n
        event: heartbeat\n data: {"ts": ...}\n\n
        data: {"error": "..."}\n\n
    """
    orchestrator = container.orchestrator
    conv_store = container.conversation_store

    history = req.history
    parent_summary: Optional[str] = None
    conv = None

    # Load history from store if conversation_id provided
    if req.conversation_id:
        conv_type = "notebook_chapter" if req.mode == "notebook" else "chat"
        conv = conv_store.get_or_create(
            conversation_id=req.conversation_id,
            type=conv_type,
            parent_id=req.parent_conversation_id,
        )
        history = conv_store.get_messages_as_llm_history(req.conversation_id, limit=20)
        if conv.parent_id:
            parent_summary = conv_store.get_parent_summary(conv.parent_id) or None

    async def _event_gen() -> AsyncIterator[str]:
        yield f"event: start\ndata: {json.dumps({'status': 'connecting'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)

        token_queue: asyncio.Queue[str | None] = asyncio.Queue()
        error_holder: list[Exception | None] = [None]
        finished = asyncio.Event()
        full_reply_parts: list[str] = []

        async def _producer() -> None:
            try:
                async for chunk in orchestrator.chat_stream(
                    req.message, history, mode=req.mode, parent_summary=parent_summary
                ):
                    await token_queue.put(chunk)
                    full_reply_parts.append(chunk)
            except Exception as e:
                error_holder[0] = e
            finally:
                finished.set()

        producer_task = asyncio.create_task(_producer())

        try:
            first_token_received = False
            while True:
                try:
                    token = await asyncio.wait_for(
                        token_queue.get(), timeout=_HEARTBEAT_INTERVAL
                    )
                except asyncio.TimeoutError:
                    if finished.is_set():
                        break
                    if not first_token_received or token_queue.empty():
                        yield f"event: heartbeat\ndata: {json.dumps({'status': 'generating'}, ensure_ascii=False)}\n\n"
                        continue
                    token = None

                if token is None:
                    if finished.is_set() and token_queue.empty():
                        break
                    continue

                first_token_received = True
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

            if error_holder[0] is not None:
                e = error_holder[0]
                if isinstance(e, LLMConfigError):
                    yield f"data: {json.dumps({'error': f'LLM 配置错误：{e}'}, ensure_ascii=False)}\n\n"
                elif isinstance(e, LLMCallError):
                    yield f"data: {json.dumps({'error': f'LLM 调用失败：{e}'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'error': f'内部错误：{type(e).__name__}: {e}'}, ensure_ascii=False)}\n\n"
            else:
                # Persist messages after successful stream completion
                full_reply = "".join(full_reply_parts).strip()
                if conv and full_reply:
                    try:
                        conv_store.add_message(conv.conversation_id, role="user", content=req.message)
                        conv_store.add_message(conv.conversation_id, role="assistant", content=full_reply)
                        # Refresh parent summary for notebook chapters (async, non-blocking)
                        if conv.parent_id and conv_store.should_refresh_summary(conv.parent_id):
                            asyncio.create_task(
                                _safe_refresh_summary(conv.parent_id, conv_store, orchestrator.llm)
                            )
                    except Exception:
                        pass  # Persistence failure should not break response
                yield f"data: {json.dumps({'done': True})}\n\n"
        finally:
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except asyncio.CancelledError:
                    pass

    return StreamingResponse(
        _event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _safe_refresh_summary(parent_id: str, conv_store, llm_provider) -> None:
    """Safely refresh parent summary in background (swallows errors)."""
    try:
        await asyncio.to_thread(conv_store.refresh_parent_summary, parent_id, llm_provider)
    except Exception:
        pass
