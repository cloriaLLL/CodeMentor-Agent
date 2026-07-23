"""CodeMentor Agent - Pydantic request/response schemas (modularized from main.py)."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Request Schemas
# --------------------------------------------------------------------------- #

class TeachRequest(BaseModel):
    node_id: str = Field(..., description="Knowledge node ID", examples=["python.advanced.decorator"])
    action: str = Field(..., description="Action type", examples=["start"])


class EcosystemSummaryRequest(BaseModel):
    node_id: str = Field(..., description="Knowledge node ID")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message", min_length=1, max_length=4000)
    history: list[dict] = Field(default_factory=list, description="Conversation history (兼容字段，有 conversation_id 时忽略)")
    mode: str = Field(default="chat", description="Chat mode: 'chat' or 'notebook'")
    conversation_id: str | None = Field(default=None, description="后端管理的对话ID")
    parent_conversation_id: str | None = Field(default=None, description="笔记本章节的父级对话ID")


class SetModelRequest(BaseModel):
    model: str = Field(..., description="Zhipu AI model ID, e.g. glm-4-flash")


# --------------------------------------------------------------------------- #
# Response Schemas
# --------------------------------------------------------------------------- #

class TeachResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    state: str = Field(..., examples=["TeachMode"])
    markdown_content: str = Field(..., description="Teaching content in Markdown")
    grounding_source: str = Field(..., description="Reference source name")
    history_notes: str = Field(..., description="Historical evolution notes")
    next_actions: list[str] = Field(..., description="Available next actions")


class CrossLanguageEquivalent(BaseModel):
    Go: str = Field(..., examples=["Gin framework Middleware (HandlerFunc chain)"])


class EcosystemSummaryResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    state: str = Field(..., examples=["EcosystemMode"])
    stack_summary: str = Field(..., description="Industry stack summary")
    cross_language_equivalent: CrossLanguageEquivalent
    next_node_recommendation: str = Field(..., examples=["python.advanced.asyncio"])


class ChatResponse(BaseModel):
    status: str = Field(..., examples=["success", "fallback"])
    reply: str = Field(..., description="Agent reply in Markdown")
    provider: str = Field(..., examples=["zhipu", "ollama", "mock"])
    degraded: bool = Field(..., description="Whether degraded to Mock mode")


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["CodeMentor Agent MVP"])
    version: str


class LLMStatusResponse(BaseModel):
    provider: str
    current_model: str
    available: bool
    degraded: bool
    is_mock: bool
    zhipu_configured: bool
    ollama_configured: bool
    available_zhipu_models: dict
    model_info: dict
    models: list[str]


class SetModelResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    model: str
    model_info: dict


class ErrorResponse(BaseModel):
    status: str = Field(default="error")
    message: str
    code: int
    detail: str | None = None


# --------------------------------------------------------------------------- #
# Learning Session Schemas (Phase 1)
# --------------------------------------------------------------------------- #

class LearnStartRequest(BaseModel):
    topic: str = Field(..., description="学习主题", examples=["Python装饰器"])
    user_id: str = Field(default="default", description="用户ID")


class LearnDiveRequest(BaseModel):
    session_id: str = Field(..., description="学习会话ID")


class LearnAdvanceRequest(BaseModel):
    session_id: str = Field(..., description="学习会话ID")


class LearnCompleteRequest(BaseModel):
    session_id: str = Field(..., description="学习会话ID")
    knowledge_point: str = Field(..., description="完成的知识点")
    score: int = Field(default=0, ge=0, le=100, description="掌握度评分")


class LearnStartResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str
    phase: str = Field(..., description="当前阶段", examples=["conversation"])
    overview: str = Field(..., description="知识点概况（Markdown）")
    prompt: str = Field(..., description="引导用户深入学习的提示")


class LearnDiveResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str
    phase: str = Field(..., examples=["teaching"])
    step: int = Field(..., description="当前教学步骤 1-4")
    step_name: str = Field(..., description="步骤名称")
    content: str = Field(..., description="教学内容（Markdown）")
    has_next: bool = Field(..., description="是否还有下一步")


class LearnAdvanceResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str
    step: int
    step_name: str
    content: str
    has_next: bool


class LearnCompleteResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str
    phase: str = Field(..., examples=["progression"])
    recommendations: list[str] = Field(..., description="推荐下一步学习内容")
    options: list[str] = Field(..., description="用户可选操作")


class LearnSessionResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str
    topic: str
    phase: str
    teaching_step: int
    context: dict


class LearnProgressResponse(BaseModel):
    status: str = Field(default="success")
    session_id: str
    progress: list[dict]


# --------------------------------------------------------------------------- #
# Exercise Schemas (Phase 1)
# --------------------------------------------------------------------------- #

class ExerciseGenerateRequest(BaseModel):
    exercise_type: str = Field(..., description="题型", examples=["understanding"])
    knowledge_point: str = Field(..., description="知识点", examples=["Python装饰器"])
    difficulty: str = Field(default="Medium", description="难度")
    subtype: str | None = Field(default=None, description="子类型（理解型用）")
    session_id: str | None = Field(default=None, description="关联学习会话")
    language: str = Field(default="python", description="编程语言")


class ExerciseSubmitRequest(BaseModel):
    exercise_type: str = Field(..., description="题型")
    question: str = Field(..., description="题目内容")
    options: list[str] | None = Field(default=None, description="选项")
    correct_answer: str | None = Field(default=None, description="正确答案")
    explanation: str | None = Field(default=None, description="解析")
    starter_code: str | None = Field(default=None, description="起始代码")
    reference_solution: str | None = Field(default=None, description="参考答案")
    test_cases: str | None = Field(default=None, description="测试用例")
    modification_requirement: str | None = Field(default=None, description="修改需求")
    acceptance_criteria: list[str] | None = Field(default=None, description="验收标准")
    evaluation_dimensions: list[str] | None = Field(default=None, description="评价维度")
    difficulty: str = Field(default="Medium")
    knowledge_points: list[str] = Field(default_factory=list)
    subtype: str | None = Field(default=None)
    user_answer: str = Field(..., description="用户答案或代码")
    session_id: str | None = Field(default=None, description="关联学习会话")
    language: str = Field(default="python", description="编程语言")


class ExerciseGenerateResponse(BaseModel):
    status: str = Field(default="success")
    exercise_id: str
    exercise_type: str
    subtype: str | None = None
    question: str
    options: list[str] | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    starter_code: str | None = None
    reference_solution: str | None = None
    test_cases: str | None = None
    modification_requirement: str | None = None
    acceptance_criteria: list[str] | None = None
    evaluation_dimensions: list[str] | None = None
    difficulty: str = "Medium"
    knowledge_points: list[str] = []
    estimated_time_min: int = 10
    language: str = Field(default="python", description="编程语言")
    conversation_id: str | None = Field(default=None, description="练习模块对话ID（供前端清除用）")
    module_key: str | None = Field(default=None, description="模块标识")


class ExerciseSubmitResponse(BaseModel):
    status: str = Field(default="success")
    passed: bool
    score: int
    result: str
    feedback: str
    needs_reteach: bool = False
    details: dict = {}


class ExerciseTypesResponse(BaseModel):
    status: str = Field(default="success")
    types: list[dict]


class LanguageInfo(BaseModel):
    """单语言运行时信息（供前端语言选择器渲染）。"""
    language: str = Field(..., description="规范语言名", examples=["python"])
    display_name: str = Field(..., description="展示名", examples=["Python"])
    file_extension: str = Field(..., description="文件扩展名", examples=[".py"])
    installed: bool = Field(..., description="本机是否已安装运行时")
    supports_tests: bool = Field(..., description="是否接入测试框架")
    is_compiled: bool = Field(..., description="是否为编译型语言")
    docker_image: str | None = Field(default=None, description="Docker 隔离镜像")


class LanguagesResponse(BaseModel):
    status: str = Field(default="success")
    languages: list[LanguageInfo]


# --------------------------------------------------------------------------- #
# Problem Cache Schemas
# --------------------------------------------------------------------------- #

class ProblemListResponse(BaseModel):
    status: str = Field(default="success")
    problems: list[dict]
    total: int


class ProblemDetailResponse(BaseModel):
    status: str = Field(default="success")
    problem: dict


class ProblemTagsResponse(BaseModel):
    status: str = Field(default="success")
    tags: list[str]
    sources: list[dict]


# --------------------------------------------------------------------------- #
# Conversation Schemas (对话存储层)
# --------------------------------------------------------------------------- #

class ConversationCreateRequest(BaseModel):
    type: str = Field(..., description="对话类型: chat/notebook_parent/notebook_chapter/exercise_module")
    title: str = Field(default="")
    parent_id: str | None = Field(default=None, description="父级对话ID（笔记本章节用）")
    module_key: str | None = Field(default=None, description="模块标识（练习模块用）")
    meta: dict = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    status: str = Field(default="success")
    conversation_id: str
    type: str
    title: str = ""
    parent_id: str | None = None
    module_key: str | None = None
    summary: str = ""
    message_count: int = 0
    created_at: str = ""


class ClearModuleRequest(BaseModel):
    language: str = Field(default="python")
    exercise_type: str = Field(..., description="题型: understanding/modification/creation/project")
    subtype: str | None = Field(default=None, description="子类型（理解型用）")


class ClearModuleResponse(BaseModel):
    status: str = Field(default="success")
    module_key: str
    cleared: bool
