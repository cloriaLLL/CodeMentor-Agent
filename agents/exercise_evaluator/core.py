"""CodeMentor Agent - 多题型练习评估器（主协调器）。

从原 922 行 God Class 拆分而来，自身只保留路由入口 + 沙箱执行编排，
代码质量评估委托给 CodeQualityAssessor，LLM 反馈生成委托给 AIFeedbackBuilder。

拆分后职责清晰：
- core.py：按 exercise_type 路由 + 沙箱执行 + 结果组装
- quality.py：纯函数代码质量评分（AST/正则启发式）
- ai_feedback.py：LLM 驱动的教学反馈生成
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from agents.exercise_evaluator.ai_feedback import AIFeedbackBuilder
from agents.exercise_evaluator.models import EvaluationResult
from agents.exercise_evaluator.quality import CodeQualityAssessor
from agents.exercise_generator import ExerciseType, GeneratedExercise
from agents.llm_client import LLMProvider, get_llm_provider_with_fallback
from agents.sandbox import (
    ExecutionResult,
    SecurityViolationError,
    run_code_simple,
    run_user_code,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class ExerciseEvaluator:
    """Evaluates exercise submissions based on exercise type.

    组合 CodeQualityAssessor（纯函数代码质量评估）与 AIFeedbackBuilder
    （LLM 反馈生成），自身只保留路由入口 + 沙箱执行编排。
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        # llm_provider 只传给 AIFeedbackBuilder，避免重复创建 LLM 客户端
        self._quality = CodeQualityAssessor()
        self._feedback = AIFeedbackBuilder(llm_provider)

    # 向后兼容：旧代码可能访问 evaluator.llm / evaluator._llm_enabled
    @property
    def llm(self) -> LLMProvider:
        return self._feedback.llm

    @property
    def _llm_enabled(self) -> bool:
        return self._feedback._llm_enabled

    async def evaluate(
        self,
        exercise: GeneratedExercise,
        user_answer: str,
    ) -> EvaluationResult:
        """Evaluate a user submission against an exercise."""
        language = getattr(exercise, "language", "python") or "python"
        if exercise.exercise_type == ExerciseType.UNDERSTANDING:
            return await self._evaluate_understanding(exercise, user_answer, language)
        elif exercise.exercise_type == ExerciseType.MODIFICATION:
            return await self._evaluate_code(exercise, user_answer, check_modification=True, language=language)
        elif exercise.exercise_type == ExerciseType.CREATION:
            return await self._evaluate_code(exercise, user_answer, check_quality=True, language=language)
        elif exercise.exercise_type == ExerciseType.PROJECT:
            return await self._evaluate_project(exercise, user_answer, language=language)
        else:
            return EvaluationResult(
                passed=False, result="error",
                feedback=f"Unknown exercise type: {exercise.exercise_type}",
            )

    # ------------------------------------------------------------------ #
    # Understanding type: instant grading + AI explanation
    # ------------------------------------------------------------------ #

    async def _evaluate_understanding(
        self, exercise: GeneratedExercise, user_answer: str, language: str = "python"
    ) -> EvaluationResult:
        """Evaluate understanding-type exercises with AI-powered explanation.

        The core principle: when a student gets it wrong, don't just say "wrong, go study".
        Instead, immediately teach the concept right there in the feedback — following
        the "三层四步教学法" philosophy: explain why, show examples, clear up misconceptions.
        """
        correct = (exercise.correct_answer or "").strip()
        user = user_answer.strip()

        # Normalize comparison
        is_correct = user.lower() == correct.lower()

        # For choice questions, also match by letter (A/B/C/D)
        if not is_correct and exercise.options:
            try:
                idx = ord(user.upper()) - ord('A')
                if 0 <= idx < len(exercise.options):
                    is_correct = exercise.options[idx].strip().lower() == correct.lower()
            except (ValueError, IndexError):
                pass

        score = 100 if is_correct else 0

        # Build base feedback with correct answer (graceful fallback for bad data)
        correct_display = correct or "（题目数据不完整，请重新生成）"
        base_explanation = exercise.explanation or ""
        # Guard against "None" string being rendered literally
        if base_explanation and base_explanation.lower() == "none":
            base_explanation = ""

        # --- AI-powered detailed feedback ---
        ai_feedback = ""
        try:
            ai_feedback = await self._feedback.generate_understanding_feedback(
                exercise=exercise,
                user_answer=user,
                correct_answer=correct_display,
                is_correct=is_correct,
                language=language,
                base_explanation=base_explanation,
            )
        except Exception as e:
            logger.warning("understanding_ai_feedback_failed", error=str(e))
            ai_feedback = ""

        # --- Assemble final feedback ---
        if ai_feedback:
            # AI feedback is the primary content; it's rich and educational
            feedback = ai_feedback
        else:
            # Fallback: structured mechanical feedback (never show "None")
            if is_correct:
                feedback = "✅ 回答正确！\n\n"
                if base_explanation:
                    feedback += f"**解析**：{base_explanation}\n\n"
                feedback += "很好，你已经掌握了这个知识点。可以尝试下一题继续巩固！"
            else:
                feedback = f"❌ 回答错误。\n\n"
                feedback += f"**正确答案**：{correct_display}\n\n"
                if base_explanation:
                    feedback += f"**解析**：{base_explanation}\n\n"
                feedback += "别灰心，仔细回顾一下这个知识点，理解为什么正确答案是对的。"

        # needs_reteach: if AI feedback is present and user got it wrong,
        # the feedback itself IS the re-teaching. Set needs_reteach=False
        # because the content already fulfills that purpose.
        needs_reteach = not is_correct and not ai_feedback

        return EvaluationResult(
            passed=is_correct,
            score=score,
            result="passed" if is_correct else "failed",
            feedback=feedback,
            needs_reteach=needs_reteach,
        )

    # ------------------------------------------------------------------ #
    # Code-based types: sandbox execution
    # ------------------------------------------------------------------ #

    async def _evaluate_code(
        self,
        exercise: GeneratedExercise,
        user_code: str,
        check_modification: bool = False,
        check_quality: bool = False,
        language: str = "python",
    ) -> EvaluationResult:
        """Evaluate code-based exercises via sandbox + LLM 综合评分。

        评分权交给 LLM：沙箱只负责跑测试获取客观事实数据，
        最终 score / passed / feedback 均由 LLM 综合判定。
        LLM 不可用时 fallback 到沙箱测试分数（纯客观）。
        """
        test_cases = exercise.test_cases or ""
        has_test_cases = bool(test_cases.strip())

        if not has_test_cases and not check_quality:
            return EvaluationResult(
                passed=False, result="error",
                feedback="No test cases available for this exercise.",
            )

        sandbox_result = None
        run_result = None
        details: dict[str, Any] = {}

        # 1. 沙箱执行（获取客观事实数据）
        if has_test_cases:
            try:
                # run_user_code 内部使用同步 subprocess，必须放到工作线程
                # 执行，避免阻塞 FastAPI 事件循环（高并发下整服务卡死）。
                sandbox_result = await asyncio.to_thread(
                    run_user_code,
                    user_code=user_code,
                    test_cases_code=test_cases,
                    language=language,
                )
            except SecurityViolationError as e:
                return EvaluationResult(
                    passed=False, result="error",
                    feedback=f"🚫 代码安全检查未通过：{e}",
                )

            details = {
                "passed_count": sandbox_result.passed_count,
                "failed_count": sandbox_result.failed_count,
                "total_count": sandbox_result.total_count,
                "pytest_summary": sandbox_result.pytest_summary,
            }
            if sandbox_result.traceback:
                details["traceback"] = sandbox_result.traceback
            # 非 python 降级模式提示
            if language != "python" and sandbox_result.pytest_summary and "exit-code mode" in sandbox_result.pytest_summary:
                details["degraded_mode"] = True
        else:
            # 无测试用例时，尝试运行代码获取输出用于反馈
            try:
                run_result = await asyncio.to_thread(
                    run_code_simple, user_code, language, timeout=10
                )
                details["run_output"] = run_result.stdout
                details["run_error"] = run_result.stderr
                details["run_status"] = run_result.status
            except Exception as e:
                details["run_error"] = str(e)

        # 2. LLM 综合评分（score + passed + feedback 全部由 LLM 给出）
        ai_result = await self._feedback.evaluate_code_with_score(
            exercise=exercise,
            user_code=user_code,
            sandbox_result=sandbox_result,
            language=language,
            run_result=run_result,
        )

        if ai_result:
            # LLM 评分可用：全部采纳 LLM 的判断
            score = ai_result["score"]
            passed = ai_result["passed"]
            feedback = ai_result["feedback"]
            details["scored_by"] = "llm"
        else:
            # LLM 不可用：fallback 到纯沙箱分数
            score = sandbox_result.score if sandbox_result else 0
            passed = score >= 60
            feedback = f"测试得分：{score}/100"
            if sandbox_result and sandbox_result.traceback:
                feedback += f"\n```\n{sandbox_result.traceback[:300]}\n```"
            details["scored_by"] = "sandbox_fallback"

        # 添加参考答案（如果有）
        if exercise.reference_solution:
            details["reference_solution"] = exercise.reference_solution

        # Modification check
        if check_modification and passed and exercise.modification_requirement:
            feedback += f"\n\n✅ 修改目标已达成：{exercise.modification_requirement}"

        needs_reteach = score < 50
        result_status = "passed" if passed else "failed"

        return EvaluationResult(
            passed=passed,
            score=score,
            result=result_status,
            feedback=feedback,
            details=details,
            needs_reteach=needs_reteach,
        )

    # ------------------------------------------------------------------ #
    # Project type: multi-dimensional evaluation
    # ------------------------------------------------------------------ #

    async def _evaluate_project(
        self, exercise: GeneratedExercise, user_code: str, language: str = "python"
    ) -> EvaluationResult:
        """Evaluate comprehensive project with LLM 综合评分。

        沙箱只跑测试获取客观数据，最终评分交给 LLM。
        LLM 不可用时 fallback 到沙箱分数。
        """
        test_cases = exercise.test_cases or ""
        if not test_cases.strip():
            return EvaluationResult(
                passed=False, result="error",
                feedback="No test cases available for this project.",
            )

        try:
            sandbox_result = await asyncio.to_thread(
                run_user_code,
                user_code=user_code,
                test_cases_code=test_cases,
                language=language,
            )
        except SecurityViolationError as e:
            return EvaluationResult(
                passed=False, result="error",
                feedback=f"🚫 代码安全检查未通过：{e}",
            )

        details = {
            "passed_count": sandbox_result.passed_count,
            "failed_count": sandbox_result.failed_count,
            "total_count": sandbox_result.total_count,
            "pytest_summary": sandbox_result.pytest_summary,
        }
        if sandbox_result.traceback:
            details["traceback"] = sandbox_result.traceback

        # LLM 综合评分
        ai_result = await self._feedback.evaluate_code_with_score(
            exercise=exercise,
            user_code=user_code,
            sandbox_result=sandbox_result,
            language=language,
            is_project=True,
        )

        if ai_result:
            score = ai_result["score"]
            passed = ai_result["passed"]
            feedback = ai_result["feedback"]
            details["scored_by"] = "llm"
        else:
            score = sandbox_result.score
            passed = score >= 60
            feedback = f"项目测试得分：{score}/100\n\n{sandbox_result.pytest_summary}"
            details["scored_by"] = "sandbox_fallback"

        if exercise.reference_solution:
            details["reference_solution"] = exercise.reference_solution

        return EvaluationResult(
            passed=passed,
            score=score,
            result="passed" if passed else "failed",
            feedback=feedback,
            details=details,
            needs_reteach=score < 50,
        )
