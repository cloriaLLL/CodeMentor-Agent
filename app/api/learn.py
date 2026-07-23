"""Teaching flow control API - Three-layer teaching structure.

Layer 1 (Conversation): User starts learning, gets brief overview
Layer 2 (Teaching): Agent runs 4-step rhythm (example→concept→tracing→exercise)
Layer 3 (Progression): User chooses to continue, pause, or review
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from agents.orchestrator import OrchestratorAgent
from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.schemas import (
    LearnStartRequest,
    LearnStartResponse,
    LearnDiveRequest,
    LearnDiveResponse,
    LearnAdvanceRequest,
    LearnAdvanceResponse,
    LearnCompleteRequest,
    LearnCompleteResponse,
    LearnSessionResponse,
    LearnProgressResponse,
)
from app.services.learning_state import (
    LearningStateService,
    PHASE_CONVERSATION,
    PHASE_TEACHING,
    PHASE_PROGRESSION,
    STEP_NAMES,
    STEP_EXAMPLE,
    STEP_EXERCISE,
)

logger = get_logger(__name__)
router = APIRouter()


def _get_state_service(container: AppContainer) -> LearningStateService:
    """Get or create learning state service."""
    if not hasattr(container, "_learning_state"):
        container._learning_state = LearningStateService()
    return container._learning_state


def _get_orchestrator(container: AppContainer) -> OrchestratorAgent:
    return container.orchestrator


# --------------------------------------------------------------------------- #
# Layer 1: Conversation - User initiates learning
# --------------------------------------------------------------------------- #

@router.post("/learn/start", response_model=LearnStartResponse)
async def learn_start(
    req: LearnStartRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> LearnStartResponse:
    """Layer 1: User initiates a learning topic, agent returns brief overview.

    Agent provides a concise overview (<200 words) and asks if user wants to dive deep.
    The session is created in 'conversation' phase, waiting for user's decision.
    """
    state_service = _get_state_service(container)
    orchestrator = _get_orchestrator(container)

    # Create learning session
    session = state_service.create_session(topic=req.topic, user_id=req.user_id)

    # Generate brief overview via LLM
    overview_prompt = (
        f"用户想学习：{req.topic}\n\n"
        "请按照三层教学结构的第一层（对话层）要求：\n"
        "1. 用不超过200字给出这个知识点的简短概况\n"
        "2. 一句话说清它是什么\n"
        "3. 列出2-3个典型应用场景\n"
        "4. 说明它在技术栈中的定位\n"
        "5. 最后用一句话引导用户决定是否深入\n\n"
        "直接输出Markdown内容，不要额外解释。"
    )

    try:
        overview = await orchestrator.chat(overview_prompt, history=[])
    except Exception as e:
        logger.warning("learn_start_llm_failed", error=str(e))
        overview = (
            f"## {req.topic}\n\n"
            f"这是关于「{req.topic}」的简短概况。\n\n"
            "（当前为Mock模式，配置LLM后将获得更详细的概况）\n\n"
            "> 想深入学这个吗？我可以从实例开始带你过一遍。"
        )

    return LearnStartResponse(
        session_id=session.session_id,
        phase=PHASE_CONVERSATION,
        overview=overview,
        prompt="想深入学这个吗？我可以从实例开始带你过一遍。",
    )


# --------------------------------------------------------------------------- #
# Layer 2: Teaching - Agent runs 4-step rhythm
# --------------------------------------------------------------------------- #

@router.post("/learn/dive", response_model=LearnDiveResponse)
async def learn_dive(
    req: LearnDiveRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> LearnDiveResponse:
    """Layer 2: User chooses to dive deep. Agent starts 4-step teaching rhythm.

    Step 1: 实例先行 (Example first) - Show runnable code
    """
    state_service = _get_state_service(container)
    orchestrator = _get_orchestrator(container)

    session = state_service.get_session(req.session_id)
    if session is None:
        raise AppError(f"Session not found: {req.session_id}", status_code=404, code="SESSION_NOT_FOUND")

    # Transition to teaching phase
    session = state_service.start_teaching(req.session_id)
    if session is None:
        raise AppError(f"Failed to start teaching phase", status_code=500, code="STATE_ERROR")

    # Generate Step 1: 实例先行
    step_prompt = (
        f"用户要深入学习：{session.topic}\n\n"
        "现在进入教学层第1步「实例先行」：\n"
        "1. 给出一个具体的、能运行的Python代码示例\n"
        "2. 代码必须完整可运行（含import）\n"
        "3. 用最简示例展示核心用法\n"
        "4. 注释只标关键行\n"
        "5. 先不解释概念，让用户'看到'效果\n"
        "6. 最后用一句短话过渡到下一步\n\n"
        "直接输出Markdown内容。"
    )

    try:
        content = await orchestrator.chat(step_prompt, history=[])
    except Exception as e:
        logger.warning("learn_dive_llm_failed", error=str(e))
        content = f"## 第1步：实例先行\n\n（Mock模式）这里将展示关于「{session.topic}」的可运行代码示例。"

    return LearnDiveResponse(
        session_id=req.session_id,
        phase=PHASE_TEACHING,
        step=STEP_EXAMPLE,
        step_name=STEP_NAMES[STEP_EXAMPLE],
        content=content,
        has_next=True,
    )


@router.post("/learn/advance", response_model=LearnAdvanceResponse)
async def learn_advance(
    req: LearnAdvanceRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> LearnAdvanceResponse:
    """Layer 2: Advance to the next teaching step.

    Steps: 2(概念跟进) → 3(溯源深化) → 4(练习巩固)
    """
    state_service = _get_state_service(container)
    orchestrator = _get_orchestrator(container)

    session = state_service.get_session(req.session_id)
    if session is None:
        raise AppError(f"Session not found: {req.session_id}", status_code=404, code="SESSION_NOT_FOUND")

    if session.phase != PHASE_TEACHING:
        raise AppError(
            f"Cannot advance: session is in '{session.phase}' phase, not 'teaching'",
            status_code=400, code="INVALID_PHASE",
        )

    next_step = session.teaching_step + 1
    if next_step > STEP_EXERCISE:
        raise AppError("Already at the last teaching step", status_code=400, code="ALREADY_AT_END")

    step_prompts = {
        2: (
            f"用户正在学习：{session.topic}\n"
            "现在进入教学层第2步「概念跟进」：\n"
            "1. 精确定义（配合类比）\n"
            "2. 语法/API详解（参数、返回值、类型）\n"
            "3. 版本差异（如有）\n"
            "4. 用一句短话过渡到下一步\n\n"
            "直接输出Markdown内容。"
        ),
        3: (
            f"用户正在学习：{session.topic}\n"
            "现在进入教学层第3步「溯源深化」：\n"
            "1. 设计哲学 / 工程取舍\n"
            "2. 历史演进（为什么从旧方案迁移到现在）\n"
            "3. 常见误区和陷阱\n"
            "4. 最佳实践\n"
            "5. 用一句短话过渡到下一步\n\n"
            "直接输出Markdown内容。"
        ),
        4: (
            f"用户正在学习：{session.topic}\n"
            "现在进入教学层第4步「练习巩固」：\n"
            "1. 出一个场景化题目验证用户掌握\n"
            "2. 题目贴近真实开发场景\n"
            "3. 由浅入深：先概念理解，再代码实现\n"
            "4. 给出题目后等待用户作答\n\n"
            "直接输出Markdown内容。"
        ),
    }

    prompt = step_prompts.get(next_step, "")
    if not prompt:
        raise AppError(f"Unknown step: {next_step}", status_code=400, code="UNKNOWN_STEP")

    try:
        content = await orchestrator.chat(prompt, history=[])
    except Exception as e:
        logger.warning("learn_advance_llm_failed", error=str(e), step=next_step)
        content = f"## 第{next_step}步：{STEP_NAMES.get(next_step, '')}\n\n（Mock模式）教学内容。"

    # Advance state
    state_service.update_session(req.session_id, teaching_step=next_step)
    if next_step >= STEP_EXERCISE:
        state_service.update_session(req.session_id, phase=PHASE_PROGRESSION)

    has_next = next_step < STEP_EXERCISE

    return LearnAdvanceResponse(
        session_id=req.session_id,
        step=next_step,
        step_name=STEP_NAMES.get(next_step, ""),
        content=content,
        has_next=has_next,
    )


# --------------------------------------------------------------------------- #
# Layer 3: Progression - User chooses next action
# --------------------------------------------------------------------------- #

@router.post("/learn/complete", response_model=LearnCompleteResponse)
async def learn_complete(
    req: LearnCompleteRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> LearnCompleteResponse:
    """Layer 3: Knowledge point completed. Agent recommends next steps.

    User can choose: continue learning, pause, or review.
    """
    state_service = _get_state_service(container)
    orchestrator = _get_orchestrator(container)

    session = state_service.get_session(req.session_id)
    if session is None:
        raise AppError(f"Session not found: {req.session_id}", status_code=404, code="SESSION_NOT_FOUND")

    # Record progress
    state_service.complete_knowledge_point(
        req.session_id, req.knowledge_point, req.score
    )

    # Generate recommendations
    rec_prompt = (
        f"用户刚完成了「{req.knowledge_point}」的学习，掌握度：{req.score}/100。\n"
        f"原始学习主题：{session.topic}\n\n"
        "请推荐2-3个相关的后续知识点，每个用一句话说明为什么推荐。\n"
        "格式：\n"
        "- **知识点名称**：推荐理由\n\n"
        "直接输出推荐列表。"
    )

    try:
        recommendations_text = await orchestrator.chat(rec_prompt, history=[])
        # Extract recommendations as list
        import re
        recommendations = re.findall(r'\*\*(.+?)\*\*', recommendations_text)
        if not recommendations:
            recommendations = [f"继续深入学习 {session.topic} 的相关内容"]
    except Exception as e:
        logger.warning("learn_complete_llm_failed", error=str(e))
        recommendations = [f"继续深入学习 {session.topic} 的相关内容"]

    return LearnCompleteResponse(
        session_id=req.session_id,
        phase=PHASE_PROGRESSION,
        recommendations=recommendations,
        options=["继续学习下一个知识点", "停下来消化一下", "回头复习这个知识点"],
    )


# --------------------------------------------------------------------------- #
# Session & Progress queries
# --------------------------------------------------------------------------- #

@router.get("/learn/session/{session_id}", response_model=LearnSessionResponse)
async def get_session(
    session_id: str,
    container: AppContainer = Depends(get_container_from_request),
) -> LearnSessionResponse:
    """Get current session state."""
    state_service = _get_state_service(container)
    session = state_service.get_session(session_id)
    if session is None:
        raise AppError(f"Session not found: {session_id}", status_code=404, code="SESSION_NOT_FOUND")

    return LearnSessionResponse(
        session_id=session.session_id,
        topic=session.topic,
        phase=session.phase,
        teaching_step=session.teaching_step,
        context=session.context,
    )


@router.get("/learn/progress/{session_id}", response_model=LearnProgressResponse)
async def get_progress(
    session_id: str,
    container: AppContainer = Depends(get_container_from_request),
) -> LearnProgressResponse:
    """Get learning progress for a session."""
    state_service = _get_state_service(container)
    progress = state_service.get_progress(session_id)
    return LearnProgressResponse(
        session_id=session_id,
        progress=progress,
    )
