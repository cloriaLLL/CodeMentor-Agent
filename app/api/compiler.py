"""CodeMentor Agent — 编译器 API 端点。

提供编译、IDE 语言服务（补全/诊断/悬停/签名）的 HTTP 接口。
完全复刻现有 exercise.py 的端点风格（Depends + AppError + Pydantic）。

端点：
- POST /api/compiler/compile    编译（可选执行）
- POST /api/compiler/lint       实时诊断（高频，防抖 150ms）
- POST /api/compiler/complete   自动补全
- POST /api/compiler/hover      悬停提示
- POST /api/compiler/signature  签名帮助

依据：DOC-05 §2.3 HTTP API 端点
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.core.exceptions import AppError
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# 请求/响应模型
# --------------------------------------------------------------------------- #

class CompileRequest(BaseModel):
    code: str = Field(..., max_length=50000, description="源代码")
    language: str = Field(default="minilang", description="源语言")
    target: str = Field(default="python", description="目标语言")
    run: bool = Field(default=False, description="是否编译后执行")


class CompileResponse(BaseModel):
    status: str = Field(default="success")
    target_code: str = Field(default="", description="编译产物")
    diagnostics: list[dict] = Field(default_factory=list)
    error: str = Field(default="", description="错误信息（status=error 时）")
    from_cache: bool = Field(default=False)
    elapsed_sec: float = Field(default=0.0)
    execution_result: dict | None = Field(default=None)


class LintRequest(BaseModel):
    code: str = Field(..., max_length=50000)
    language: str = Field(default="minilang")


class LintResponse(BaseModel):
    diagnostics: list[dict] = Field(default_factory=list)


class CompleteRequest(BaseModel):
    code: str = Field(..., max_length=50000)
    cursor_offset: int = Field(..., ge=0, description="光标字符偏移（0-based）")
    language: str = Field(default="minilang")


class CompleteResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)


class HoverRequest(BaseModel):
    code: str = Field(..., max_length=50000)
    offset: int = Field(..., ge=0)
    language: str = Field(default="minilang")


class HoverResponse(BaseModel):
    result: dict | None = Field(default=None)


class SignatureRequest(BaseModel):
    code: str = Field(..., max_length=50000)
    offset: int = Field(..., ge=0)
    language: str = Field(default="minilang")


class SignatureResponse(BaseModel):
    result: dict | None = Field(default=None)


# --------------------------------------------------------------------------- #
# 端点实现
# --------------------------------------------------------------------------- #

@router.post("/compiler/compile", response_model=CompileResponse)
async def compile_code(
    req: CompileRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> CompileResponse:
    """编译源代码，可选附带执行。

    集成四层安全防御：
    1. 输入验证（长度/深度/字符集）
    2. 编译沙箱（超时/递归限制）
    3. AST 白名单安全校验
    4. 编译产物二次校验（执行时由 run_code_simple 触发）
    """
    service = container.compiler_service
    result = service.compile(
        source=req.code,
        language=req.language,
        target=req.target,
        run=req.run,
    )
    return CompileResponse(
        status=result.get("status", "error"),
        target_code=result.get("target_code", ""),
        diagnostics=result.get("diagnostics", []),
        error=result.get("error", ""),
        from_cache=result.get("from_cache", False),
        elapsed_sec=result.get("elapsed_sec", 0.0),
        execution_result=result.get("execution_result"),
    )


@router.post("/compiler/lint", response_model=LintResponse)
async def lint_code(
    req: LintRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> LintResponse:
    """实时诊断（IDE 高频调用，前端防抖 150ms）。"""
    service = container.compiler_service
    diags = service.lint(req.code, req.language)
    return LintResponse(diagnostics=diags)


@router.post("/compiler/complete", response_model=CompleteResponse)
async def complete_code(
    req: CompleteRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> CompleteResponse:
    """自动补全。"""
    service = container.compiler_service
    items = service.complete(req.code, req.cursor_offset, req.language)
    return CompleteResponse(items=items)


@router.post("/compiler/hover", response_model=HoverResponse)
async def hover_code(
    req: HoverRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> HoverResponse:
    """悬停提示。"""
    service = container.compiler_service
    result = service.hover(req.code, req.offset, req.language)
    return HoverResponse(result=result)


@router.post("/compiler/signature", response_model=SignatureResponse)
async def signature_code(
    req: SignatureRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> SignatureResponse:
    """签名帮助。"""
    service = container.compiler_service
    result = service.signature_help(req.code, req.offset, req.language)
    return SignatureResponse(result=result)
