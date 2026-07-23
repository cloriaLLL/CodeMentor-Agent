"""CodeMentor Agent - AI 反馈生成器（依赖 LLM）。

从原 ExerciseEvaluator 拆分出的 5 个反馈生成方法，负责：
- 理解题的 AI 详细解析（generate_understanding_feedback）
- 代码题的 AI 智能反馈（generate_code_feedback）
- system prompt 构建（_build_*_system_prompt，子任务 C 将外置到 prompts/）
- user message 组装（_build_ai_feedback_user_message）
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from agents import load_prompt
from agents.exercise_generator import GeneratedExercise
from agents.llm_client import LLMProvider, get_llm_provider_with_fallback
from agents.sandbox import ExecutionResult
from app.core.logger import get_logger

logger = get_logger(__name__)


class AIFeedbackBuilder:
    """LLM 反馈生成器，遵循"三层四步教学法"精神。

    所有 generate_* 方法在 LLM 不可用或调用失败时返回空字符串（优雅降级），
    由调用方（core.py）决定 fallback 行为。
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self.llm = llm_provider or get_llm_provider_with_fallback()
        self._llm_enabled = self.llm.name != "mock"

    # ------------------------------------------------------------------ #
    # 理解题反馈
    # ------------------------------------------------------------------ #

    async def generate_understanding_feedback(
        self,
        exercise: GeneratedExercise,
        user_answer: str,
        correct_answer: str,
        is_correct: bool,
        language: str,
        base_explanation: str,
    ) -> str:
        """Generate AI-powered detailed feedback for understanding-type exercises.

        Follows CodeMentor's teaching philosophy:
        - Positive reinforcement first (what they did well)
        - Clear explanation of the correct answer
        - Why wrong answers are wrong (for choice questions)
        - Common misconceptions cleared up
        - Real-world analogy to aid understanding
        - Encouraging tone

        Returns empty string if LLM is unavailable or fails.
        """
        if not self._llm_enabled:
            return ""

        kp = exercise.knowledge_points[0] if exercise.knowledge_points else "编程基础"
        options_text = ""
        if exercise.options:
            options_lines = []
            for i, opt in enumerate(exercise.options):
                letter = chr(65 + i)
                options_lines.append(f"{letter}. {opt}")
            options_text = "\n".join(options_lines)

        result_label = "✅ 回答正确！" if is_correct else "❌ 回答错误"

        sys_prompt = self._build_understanding_feedback_system_prompt()
        user_msg = f"""## 题目信息

**知识点**：{kp}
**编程语言**：{language}
**题目**：
{exercise.question}

{"**选项**：\n" + options_text if options_text else ""}

## 答题情况

**学生答案**：{user_answer}
**正确答案**：{correct_answer}
**结果**：{result_label}

{"**原有解析**：" + base_explanation if base_explanation else "（无原有解析）"}

请根据以上信息，给出符合 CodeMentor 教学风格的详细反馈。"""

        try:
            response = await self.llm.chat(
                system_prompt=sys_prompt,
                user_message=user_msg,
                temperature=0.7,
                max_tokens=1500,
            )
            return response.strip()
        except Exception as e:
            logger.warning("understanding_ai_feedback_call_failed", error=str(e))
            return ""

    def _build_understanding_feedback_system_prompt(self) -> str:
        """Build system prompt for understanding exercise feedback.

        Follows the "三层四步教学法" spirit adapted for exercise feedback:
        Layer 1 (感知): show the correct answer clearly
        Layer 2 (理解): explain why it's correct, why others are wrong
        Layer 3 (应用): connect to real-world usage / common pitfalls

        Note: 子任务 C 将把此内嵌字符串外置到 prompts/feedback_understanding.txt。
        """
        return load_prompt("feedback_understanding")

    # ------------------------------------------------------------------ #
    # 代码题反馈
    # ------------------------------------------------------------------ #

    async def evaluate_code_with_score(
        self,
        exercise: GeneratedExercise,
        user_code: str,
        sandbox_result: Optional[ExecutionResult] = None,
        language: str = "python",
        run_result: Optional[Any] = None,
        is_project: bool = False,
        dimension_scores: Optional[dict[str, int]] = None,
    ) -> Optional[dict]:
        """让 LLM 综合评分并返回结构化结果。

        返回 dict: {score: int, passed: bool, feedback: str}
        LLM 不可用或解析失败时返回 None（由调用方 fallback）。
        """
        if not self._llm_enabled:
            return None

        try:
            system_prompt = self._build_ai_feedback_system_prompt()
            user_message = self._build_ai_feedback_user_message(
                exercise=exercise,
                user_code=user_code,
                sandbox_result=sandbox_result,
                language=language,
                run_result=run_result,
                is_project=is_project,
                dimension_scores=dimension_scores,
            )

            response = await self.llm.chat(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                max_tokens=3000,
            )
            return self._parse_score_response(response.strip())
        except Exception as e:
            logger.warning("ai_score_evaluation_failed", error=str(e))
            return None

    def _parse_score_response(self, text: str) -> Optional[dict]:
        """从 LLM 响应中解析 JSON 评分结果。

        LLM 可能把 JSON 包在 ```json 代码块里，也可能直接输出。
        feedback 字段里可能包含任意字符（含花括号、反引号），
        所以统一用括号计数法找最外层 JSON 对象边界。
        """
        if not text:
            return None

        # 找第一个 { 的位置（可能在 ```json 代码块内，也可能直接在文本中）
        start = text.find("{")
        if start == -1:
            return None

        end = self._find_matching_brace(text, start)
        if end == -1:
            return None

        json_str = text[start : end + 1]
        return self._try_parse_json(json_str)

    @staticmethod
    def _find_matching_brace(text: str, start: int) -> int:
        """从 start 位置的 { 开始，找到匹配的 }，返回其索引。找不到返回 -1。

        正确处理字符串中的花括号（简单跳过双引号字符串内容）。
        """
        depth = 0
        i = start
        in_string = False
        escape = False
        while i < len(text):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return i
            i += 1
        return -1

    def _try_parse_json(self, json_str: str) -> Optional[dict]:
        """尝试解析 JSON，成功返回评分 dict，失败返回 None。

        LLM 有时会在字符串里输出真实换行（而非 \n 转义），
        用 strict=False 容忍控制字符。
        """
        try:
            data = json.loads(json_str, strict=False)
            score = int(data.get("score", 0))
            passed = bool(data.get("passed", score >= 60))
            feedback = str(data.get("feedback", "")).strip()
            score = max(0, min(100, score))
            return {"score": score, "passed": passed, "feedback": feedback}
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("ai_score_parse_failed", snippet=json_str[:200])
            return None

    async def generate_code_feedback(
        self,
        exercise: GeneratedExercise,
        user_code: str,
        sandbox_result: Optional[ExecutionResult] = None,
        language: str = "python",
        run_result: Optional[Any] = None,
        is_project: bool = False,
        dimension_scores: Optional[dict[str, int]] = None,
    ) -> str:
        """Generate AI-powered detailed feedback for code exercises.

        Uses the "三层四步教学法" spirit:
        - Warm, encouraging tone
        - Start with what the student did right (positive reinforcement)
        - Then explain what went wrong clearly
        - Give specific, actionable suggestions
        - Don't just give the answer - guide the student to figure it out
        - Include code quality observations
        - End with encouragement

        注意：此方法仅返回反馈文本。如需结构化评分，请用 evaluate_code_with_score。
        """
        result = await self.evaluate_code_with_score(
            exercise=exercise,
            user_code=user_code,
            sandbox_result=sandbox_result,
            language=language,
            run_result=run_result,
            is_project=is_project,
            dimension_scores=dimension_scores,
        )
        return result["feedback"] if result else ""

    def _build_ai_feedback_system_prompt(self) -> str:
        """Build system prompt for AI feedback generation.

        Note: 子任务 C 将把此内嵌字符串外置到 prompts/feedback_code.txt。
        """
        return load_prompt("feedback_code")

    def _build_ai_feedback_user_message(
        self,
        exercise: GeneratedExercise,
        user_code: str,
        sandbox_result: Optional[ExecutionResult] = None,
        language: str = "python",
        run_result: Optional[Any] = None,
        is_project: bool = False,
        dimension_scores: Optional[dict[str, int]] = None,
    ) -> str:
        """Build user message for AI feedback generation."""
        parts: list[str] = []

        parts.append(f"## 题目信息")
        parts.append(f"题型：{exercise.exercise_type.value}")
        parts.append(f"编程语言：{language}")
        parts.append(f"难度：{exercise.difficulty}")
        if exercise.knowledge_points:
            parts.append(f"知识点：{', '.join(exercise.knowledge_points)}")
        parts.append("")

        parts.append(f"## 题目描述")
        parts.append(exercise.question)
        parts.append("")

        exercise_type_desc = "项目题" if is_project else "代码题"
        parts.append(f"## 学生提交的{exercise_type_desc}")
        parts.append(f"```{language}")
        parts.append(user_code)
        parts.append("```")
        parts.append("")

        if sandbox_result:
            parts.append("## 测试结果")
            parts.append(f"状态：{sandbox_result.status}")
            parts.append(f"通过：{sandbox_result.passed_count}/{sandbox_result.total_count}")
            parts.append(f"失败：{sandbox_result.failed_count}")
            parts.append(f"得分：{sandbox_result.score}/100")
            if sandbox_result.pytest_summary:
                parts.append(f"测试摘要：{sandbox_result.pytest_summary}")
            if sandbox_result.traceback:
                parts.append(f"错误追踪：")
                parts.append("```")
                parts.append(sandbox_result.traceback[:1000])
                parts.append("```")
            parts.append("")

        if run_result:
            parts.append("## 代码运行结果")
            parts.append(f"状态：{run_result.status}")
            if run_result.stdout:
                parts.append(f"标准输出：")
                parts.append("```")
                parts.append(run_result.stdout[:500])
                parts.append("```")
            if run_result.stderr:
                parts.append(f"错误输出：")
                parts.append("```")
                parts.append(run_result.stderr[:500])
                parts.append("```")
            parts.append("")

        if is_project and dimension_scores:
            parts.append("## 各维度得分")
            for dim, score in dimension_scores.items():
                parts.append(f"- {dim}：{score}/100")
            parts.append("")

        if exercise.reference_solution:
            parts.append("## 参考答案（仅供你参考，不要直接告诉学生）")
            parts.append(f"```{language}")
            parts.append(exercise.reference_solution)
            parts.append("```")
            parts.append("")

        if exercise.modification_requirement:
            parts.append(f"## 修改要求")
            parts.append(exercise.modification_requirement)
            parts.append("")

        if exercise.acceptance_criteria:
            parts.append("## 验收标准")
            for i, criteria in enumerate(exercise.acceptance_criteria, 1):
                parts.append(f"{i}. {criteria}")
            parts.append("")

        parts.append("请根据以上信息，给学生提供详细的反馈。记住：温暖鼓励，具体建议，引导思考！")

        return "\n".join(parts)
