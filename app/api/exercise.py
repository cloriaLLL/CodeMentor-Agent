"""Multi-exercise type system API.

Supports four exercise types:
1. Understanding (choice/truefalse/fillblank) - instant grading
2. Modification - base code + modification task + sandbox validation
3. Creation - requirements + test cases + sandbox + quality scoring
4. Project - module-level + multi-dimensional evaluation

Also provides access to cached external problems (LeetCode, interview questions, etc.)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from agents.exercise_generator import ExerciseType, GeneratedExercise
from agents.sandbox import (
    ExecutionError,
    SecurityViolationError,
    UnsupportedLanguageError,
    run_code_simple,
)
from agents.sandbox_runtime import list_runtimes
from app.api.deps import get_container_from_request
from app.core.container import AppContainer
from app.core.exceptions import AppError
from app.core.logger import get_logger
from app.schemas import (
    ExerciseGenerateRequest,
    ExerciseGenerateResponse,
    ExerciseSubmitRequest,
    ExerciseSubmitResponse,
    ExerciseTypesResponse,
    LanguageInfo,
    LanguagesResponse,
    ProblemListResponse,
    ProblemDetailResponse,
    ProblemTagsResponse,
    ClearModuleRequest,
    ClearModuleResponse,
)

logger = get_logger(__name__)
router = APIRouter()


# --------------------------------------------------------------------------- #
# Exercise type info
# --------------------------------------------------------------------------- #

@router.get("/exercise/types", response_model=ExerciseTypesResponse)
async def get_exercise_types(
    container: AppContainer = Depends(get_container_from_request),
) -> ExerciseTypesResponse:
    """Get all supported exercise types and subtypes."""
    return ExerciseTypesResponse(types=container.exercise_service.get_supported_types())


# --------------------------------------------------------------------------- #
# Exercise generation
# --------------------------------------------------------------------------- #

@router.post("/exercise/generate", response_model=ExerciseGenerateResponse)
async def generate_exercise(
    req: ExerciseGenerateRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> ExerciseGenerateResponse:
    """Generate an exercise of the specified type."""
    service = container.exercise_service

    try:
        exercise, conversation_id, module_key = await service.generate_exercise(
            exercise_type=req.exercise_type,
            knowledge_point=req.knowledge_point,
            difficulty=req.difficulty,
            subtype=req.subtype,
            session_id=req.session_id,
            language=req.language,
        )
    except ValueError as e:
        raise AppError(str(e), status_code=400, code="INVALID_EXERCISE_TYPE")

    return ExerciseGenerateResponse(
        exercise_id=exercise.exercise_id,
        exercise_type=exercise.exercise_type.value,
        subtype=exercise.subtype,
        question=exercise.question,
        options=exercise.options,
        correct_answer=exercise.correct_answer,
        explanation=exercise.explanation,
        starter_code=exercise.starter_code,
        reference_solution=exercise.reference_solution,
        test_cases=exercise.test_cases,
        modification_requirement=exercise.modification_requirement,
        acceptance_criteria=exercise.acceptance_criteria,
        evaluation_dimensions=exercise.evaluation_dimensions,
        difficulty=exercise.difficulty,
        knowledge_points=exercise.knowledge_points,
        estimated_time_min=exercise.estimated_time_min,
        language=exercise.language,
        conversation_id=conversation_id,
        module_key=module_key,
    )


# --------------------------------------------------------------------------- #
# Exercise submission and evaluation
# --------------------------------------------------------------------------- #

@router.post("/exercise/submit", response_model=ExerciseSubmitResponse)
async def submit_exercise(
    req: ExerciseSubmitRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> ExerciseSubmitResponse:
    """Submit an exercise answer/code for evaluation.

    The request contains the full exercise data (so the server is stateless
    regarding exercise content) plus the user's answer.
    """
    service = container.exercise_service

    # Reconstruct exercise from request data
    try:
        et = ExerciseType(req.exercise_type)
    except ValueError:
        raise AppError(f"Invalid exercise type: {req.exercise_type}", status_code=400, code="INVALID_TYPE")

    exercise = GeneratedExercise(
        exercise_id="submitted",
        exercise_type=et,
        subtype=req.subtype,
        question=req.question,
        options=req.options,
        correct_answer=req.correct_answer,
        explanation=req.explanation,
        starter_code=req.starter_code,
        reference_solution=req.reference_solution,
        test_cases=req.test_cases,
        modification_requirement=req.modification_requirement,
        acceptance_criteria=req.acceptance_criteria,
        evaluation_dimensions=req.evaluation_dimensions,
        difficulty=req.difficulty,
        knowledge_points=req.knowledge_points,
        language=req.language,
    )

    result = await service.evaluate_submission(
        exercise=exercise,
        user_answer=req.user_answer,
        session_id=req.session_id,
    )

    return ExerciseSubmitResponse(
        passed=result.passed,
        score=result.score,
        result=result.result,
        feedback=result.feedback,
        needs_reteach=result.needs_reteach,
        details=result.details,
    )


# --------------------------------------------------------------------------- #
# Exercise module conversation management
# --------------------------------------------------------------------------- #

@router.post("/exercise/clear-module", response_model=ClearModuleResponse)
async def clear_module_conversation(
    req: ClearModuleRequest,
    container: AppContainer = Depends(get_container_from_request),
) -> ClearModuleResponse:
    """Clear the conversation history for a specific language+exercise_type module.

    After clearing, the next exercise generation starts fresh (no prior context).
    """
    service = container.exercise_service
    module_key = service._compute_module_key(req.language, req.exercise_type, req.subtype)
    cleared = service.conv_store.clear_module_conversation(module_key)
    return ClearModuleResponse(module_key=module_key, cleared=cleared)


# --------------------------------------------------------------------------- #
# Quick code execution (for "Run" button)
# --------------------------------------------------------------------------- #

class RunCodeRequest(BaseModel):
    code: str = Field(..., description="Code to execute")
    language: str = Field(default="python", description="Programming language: python or javascript")


class RunCodeResponse(BaseModel):
    status: str = Field(default="success")
    output: str = Field(default="", description="stdout output")
    error: str = Field(default="", description="stderr or error message")
    execution_time_sec: float = Field(default=0.0)


@router.post("/exercise/run", response_model=RunCodeResponse)
async def run_code(req: RunCodeRequest) -> RunCodeResponse:
    """Execute user code in a sandbox and return stdout/stderr.

    支持所有已注册语言（python/javascript/bash/java/csharp）。
    安全检查与隔离执行统一委托给 agents.sandbox.run_code_simple，
    不再在本端点内维护重复的安全规则与 subprocess 逻辑。
    """
    code = req.code.strip()
    if not code:
        return RunCodeResponse(status="error", error="代码为空")

    try:
        result = run_code_simple(code, req.language, timeout=10)
    except SecurityViolationError as e:
        return RunCodeResponse(status="error", error=f"安全限制：{e}")
    except UnsupportedLanguageError as e:
        return RunCodeResponse(status="error", error=str(e))
    except ExecutionError as e:
        return RunCodeResponse(status="error", error=str(e))

    return RunCodeResponse(
        status="success" if result.status == "success" else "error",
        output=result.stdout,
        error=result.stderr,
        execution_time_sec=round(result.execution_time_sec, 3),
    )


@router.get("/languages", response_model=LanguagesResponse)
async def list_languages() -> LanguagesResponse:
    """列出所有已注册语言运行时及其可用性（供前端语言选择器渲染）。"""
    infos: list[LanguageInfo] = []
    for rt in list_runtimes():
        av = rt.check_availability()
        infos.append(
            LanguageInfo(
                language=rt.language,
                display_name=rt.display_name,
                file_extension=rt.file_extension,
                installed=av.installed,
                supports_tests=rt.supports_tests,
                is_compiled=rt.is_compiled,
                docker_image=rt.docker_image,
            )
        )
    return LanguagesResponse(languages=infos)


# --------------------------------------------------------------------------- #
# External problem cache
# --------------------------------------------------------------------------- #

@router.get("/problems", response_model=ProblemListResponse)
async def list_problems(
    source: str | None = Query(None, description="Filter by source"),
    tag: str | None = Query(None, description="Filter by tag"),
    difficulty: str | None = Query(None, description="Filter by difficulty"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    container: AppContainer = Depends(get_container_from_request),
) -> ProblemListResponse:
    """List cached problems with optional filtering."""
    fetcher = container.problem_fetcher
    problems = fetcher.get_problems(
        source=source, tag=tag, difficulty=difficulty, limit=limit, offset=offset
    )
    # Strip test_cases and starter_code from list view for brevity
    problems = [
        {k: v for k, v in p.items() if k not in ("test_cases", "starter_code")}
        for p in problems
    ]
    return ProblemListResponse(problems=problems, total=len(problems))


@router.get("/problems/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem(
    problem_id: int,
    container: AppContainer = Depends(get_container_from_request),
) -> ProblemDetailResponse:
    """Get full problem details by ID."""
    fetcher = container.problem_fetcher
    problem = fetcher.get_problem_by_id(problem_id)
    if problem is None:
        raise AppError(f"Problem not found: {problem_id}", status_code=404, code="PROBLEM_NOT_FOUND")
    return ProblemDetailResponse(problem=problem)


@router.get("/problems/meta/tags", response_model=ProblemTagsResponse)
async def get_problem_meta(
    container: AppContainer = Depends(get_container_from_request),
) -> ProblemTagsResponse:
    """Get all available tags and sources for problem filtering."""
    fetcher = container.problem_fetcher
    return ProblemTagsResponse(
        tags=fetcher.get_tags(),
        sources=fetcher.get_sources(),
    )


@router.post("/problems/refresh", response_model=ProblemListResponse)
async def refresh_problems(
    container: AppContainer = Depends(get_container_from_request),
) -> ProblemListResponse:
    """Refresh built-in problem cache."""
    fetcher = container.problem_fetcher
    count = fetcher.load_builtin_problems()
    problems = fetcher.get_problems(limit=100)
    problems = [
        {k: v for k, v in p.items() if k not in ("test_cases", "starter_code")}
        for p in problems
    ]
    return ProblemListResponse(problems=problems, total=len(problems))
