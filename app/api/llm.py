"""LLM provider status and model management endpoints."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from agents.llm_client import ZHIPU_MODELS, ZhipuProvider
from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.schemas import LLMStatusResponse, SetModelRequest, SetModelResponse

router = APIRouter()


@router.get("/llm_status", response_model=LLMStatusResponse)
async def llm_status(
    container: AppContainer = Depends(get_container_from_request),
) -> LLMStatusResponse:
    """Get current LLM provider status and available models."""
    orchestrator = container.orchestrator
    provider = orchestrator.llm
    provider_name = provider.name

    current_model = getattr(provider, "model", "")
    model_info = ZHIPU_MODELS.get(current_model, {})

    return LLMStatusResponse(
        provider=provider_name,
        current_model=current_model,
        available=provider_name != "mock",
        degraded=provider_name == "mock",
        is_mock=provider_name == "mock",
        zhipu_configured=bool(os.getenv("ZHIPU_API_KEY")),
        ollama_configured=bool(os.getenv("OLLAMA_HOST")),
        available_zhipu_models=ZHIPU_MODELS,
        model_info=model_info,
        models=list(ZHIPU_MODELS.keys()) if provider_name == "zhipu" else [],
    )


@router.post("/set_model")
async def set_model(
    req: SetModelRequest,
    container: AppContainer = Depends(get_container_from_request),
):
    """Runtime model switching for Zhipu provider (no restart required)."""
    orchestrator = container.orchestrator

    if orchestrator.llm.name != "zhipu":
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": (
                    f"当前 Provider 为 {orchestrator.llm.name}，无法切换模型。"
                    "请在 .env 中配置 ZHIPU_API_KEY 后重启服务。"
                ),
                "code": 400,
            },
        )

    if req.model not in ZHIPU_MODELS:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"未知模型：{req.model}。可选：{list(ZHIPU_MODELS.keys())}",
                "code": 400,
            },
        )

    api_key = os.getenv("ZHIPU_API_KEY", "")
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "未配置 ZHIPU_API_KEY，无法切换模型。",
                "code": 400,
            },
        )

    new_provider = ZhipuProvider(api_key=api_key, model=req.model)
    orchestrator.llm = new_provider
    orchestrator._llm_enabled = True

    return SetModelResponse(
        status="success",
        model=req.model,
        model_info=ZHIPU_MODELS[req.model],
    )
