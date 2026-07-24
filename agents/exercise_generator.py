"""CodeMentor Agent - Multi-type exercise generator.

Generates four types of exercises:
1. Understanding: choice / true-false / fill-in-the-blank
2. Modification: base code + modification task
3. Creation: requirements + test cases (from scratch)
4. Project: module-level comprehensive project

All exercises are generated via LLM with structured JSON output.
Falls back to seed_data when LLM is unavailable.
"""
from __future__ import annotations

import json
import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from agents import load_prompt
from agents.llm_client import (
    LLMCallError,
    LLMConfigError,
    LLMProvider,
    get_llm_provider_with_fallback,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class ExerciseType(str, Enum):
    UNDERSTANDING = "understanding"
    MODIFICATION = "modification"
    CREATION = "creation"
    PROJECT = "project"


class UnderstandingSubtype(str, Enum):
    CHOICE = "choice"
    TRUE_FALSE = "truefalse"
    FILL_BLANK = "fillblank"


class GeneratedExercise(BaseModel):
    """Unified exercise model for all types."""
    exercise_id: str = Field(..., description="练习 ID")
    exercise_type: ExerciseType = Field(..., description="题型")
    subtype: Optional[str] = Field(None, description="子类型（理解型用）")
    question: str = Field(..., description="题目内容（Markdown）")
    # Understanding type
    options: Optional[list[str]] = Field(None, description="选项（选择题用）")
    correct_answer: Optional[str] = Field(None, description="正确答案")
    explanation: Optional[str] = Field(None, description="答案解析")
    # Code-based types
    starter_code: Optional[str] = Field(None, description="起始代码骨架")
    reference_solution: Optional[str] = Field(None, description="参考答案")
    test_cases: Optional[str] = Field(None, description="pytest 测试用例")
    modification_requirement: Optional[str] = Field(None, description="修改需求（修改型用）")
    # Project type
    acceptance_criteria: Optional[list[str]] = Field(None, description="验收标准（项目题用）")
    evaluation_dimensions: Optional[list[str]] = Field(None, description="评价维度")
    # Metadata
    difficulty: str = Field(default="Medium", description="难度")
    knowledge_points: list[str] = Field(default_factory=list, description="关联知识点")
    estimated_time_min: int = Field(default=10, description="预计耗时（分钟）")
    language: str = Field(default="python", description="编程语言")


class ExerciseGeneratorAgent:
    """Multi-type exercise generator with LLM support."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self.llm = llm_provider or get_llm_provider_with_fallback()
        self._llm_enabled = self.llm.name != "mock"

    async def generate(
        self,
        exercise_type: ExerciseType,
        knowledge_point: str,
        difficulty: str = "Medium",
        subtype: Optional[str] = None,
        language: str = "python",
        conversation_messages: Optional[list[dict]] = None,
    ) -> GeneratedExercise:
        """Generate an exercise of the specified type.

        :param conversation_messages: Optional prior conversation history [{role, content}, ...].
            When provided, LLM sees previous exercises to avoid duplicates.
        """
        exercise_id = f"{exercise_type.value}_{knowledge_point[:20]}_{difficulty[:3]}"

        if not self._llm_enabled:
            return self._fallback_exercise(exercise_id, exercise_type, knowledge_point, difficulty, subtype, language)

        try:
            if exercise_type == ExerciseType.UNDERSTANDING:
                return await self._generate_understanding(exercise_id, knowledge_point, difficulty, subtype or "choice", language, conversation_messages)
            elif exercise_type == ExerciseType.MODIFICATION:
                return await self._generate_modification(exercise_id, knowledge_point, difficulty, language, conversation_messages)
            elif exercise_type == ExerciseType.CREATION:
                return await self._generate_creation(exercise_id, knowledge_point, difficulty, language, conversation_messages)
            elif exercise_type == ExerciseType.PROJECT:
                return await self._generate_project(exercise_id, knowledge_point, difficulty, language, conversation_messages)
            else:
                raise ValueError(f"Unknown exercise type: {exercise_type}")
        except (LLMCallError, LLMConfigError) as e:
            logger.warning("exercise_generation_failed, falling back", error=str(e))
            return self._fallback_exercise(exercise_id, exercise_type, knowledge_point, difficulty, subtype, language)

    def _build_messages_with_history(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_messages: Optional[list[dict]] = None,
    ) -> tuple[Optional[list[dict]], str]:
        """Build messages array with conversation history for anti-repeat.

        Returns (messages_with_history, adjusted_temperature).
        If no history, returns (None, original_behavior).
        """
        if not conversation_messages:
            return None, ""

        anti_repeat = (
            "\n\n--- 注意 ---\n"
            "以上是你之前生成的题目。请生成一道**全新的、不同的**题目，"
            "避免与上述任何题目重复（可以从不同角度考察相同知识点，或使用不同场景）。"
        )
        messages = [{"role": "system", "content": system_prompt}] + conversation_messages + [
            {"role": "user", "content": user_prompt + anti_repeat}
        ]
        return messages, "0.85"

    async def _generate_understanding(
        self, exercise_id: str, kp: str, difficulty: str, subtype: str,
        language: str = "python",
        conversation_messages: Optional[list[dict]] = None,
    ) -> GeneratedExercise:
        subtype_desc = {
            "choice": "选择题（4个选项）",
            "truefalse": "判断题",
            "fillblank": "填空题",
        }.get(subtype, "选择题")

        sys_prompt = "你是一位编程教育专家，擅长出考察概念理解的题目。题目必须语言准确、选项无歧义、解析详实。"
        user_prompt = load_prompt("exercise_understanding").format(
            subtype_desc=subtype_desc, knowledge_point=kp, difficulty=difficulty, language=language
        )
        messages_with_history, _ = self._build_messages_with_history(sys_prompt, user_prompt, conversation_messages)

        response = await self.llm.chat(
            system_prompt=sys_prompt,
            user_message=user_prompt,
            temperature=0.85 if messages_with_history else 0.7,
            max_tokens=1500,
            messages=messages_with_history,
        )
        data = self._parse_json(response)

        # --- Quality validation & sanitization ---
        question = (data.get("question") or "").strip()
        options = data.get("options")
        correct_answer = (data.get("correct_answer") or "").strip()
        explanation = (data.get("explanation") or "").strip()

        # Guard against "None" string (LLM occasionally outputs literal "None")
        if explanation.lower() == "none":
            explanation = ""
        if correct_answer.lower() == "none":
            correct_answer = ""

        # For choice questions: validate options and correct answer
        if subtype == "choice" and isinstance(options, list) and len(options) >= 2:
            # Normalize correct_answer: if it's the option text, find its letter
            if correct_answer and len(correct_answer) > 1:
                for i, opt in enumerate(options):
                    if opt.strip().lower() == correct_answer.strip().lower():
                        correct_answer = chr(65 + i)
                        break
            # If correct_answer is a letter, validate range
            if len(correct_answer) == 1 and correct_answer.upper() in "ABCDEFGH":
                idx = ord(correct_answer.upper()) - ord('A')
                if idx >= len(options):
                    correct_answer = "A"
            elif not correct_answer:
                correct_answer = "A"

        # For true/false questions
        if subtype == "truefalse":
            if correct_answer in ["对", "True", "true", "T", "正确", "是", "√"]:
                correct_answer = "正确"
            elif correct_answer in ["错", "False", "false", "F", "错误", "否", "×"]:
                correct_answer = "错误"
            elif isinstance(options, list) and len(options) >= 2:
                # LLM 可能返回选择题格式，根据 correct_answer 字母判断对错
                if len(correct_answer) == 1 and correct_answer.upper() in "AB":
                    idx = ord(correct_answer.upper()) - ord("A")
                    opt_text = options[idx].strip().lower()
                    correct_answer = "正确" if any(k in opt_text for k in ["正确", "对", "true", "是"]) else "错误"
                else:
                    correct_answer = "正确"
            else:
                correct_answer = "正确"
            options = ["正确", "错误"]

        # For fill-in-the-blank questions
        if subtype == "fillblank":
            # LLM 可能返回选择题格式，需要提取正确答案文本
            if isinstance(options, list) and len(options) >= 2 and correct_answer:
                if len(correct_answer) == 1 and correct_answer.upper() in "ABCDEFGH":
                    idx = ord(correct_answer.upper()) - ord("A")
                    if idx < len(options):
                        # 从正确选项中提取答案（去掉 A. 前缀等）
                        opt_text = options[idx].strip()
                        for prefix in ["A.", "B.", "C.", "D.", "E.", "A、", "B、", "C、", "D、", "E、", "A ", "B ", "C ", "D ", "E "]:
                            if opt_text.startswith(prefix):
                                opt_text = opt_text[len(prefix):].strip()
                                break
                        correct_answer = opt_text
            # 强制 options 为 null（填空题没有选项）
            options = None

        # Fallback for empty question (shouldn't happen, but guard anyway)
        if not question:
            question = f"关于 {kp} 的理解题"

        return GeneratedExercise(
            exercise_id=exercise_id,
            exercise_type=ExerciseType.UNDERSTANDING,
            subtype=subtype,
            question=question,
            options=options if isinstance(options, list) else None,
            correct_answer=correct_answer,
            explanation=explanation,
            difficulty=difficulty,
            knowledge_points=[kp],
            language=language,
        )

    async def _generate_modification(
        self, exercise_id: str, kp: str, difficulty: str,
        language: str = "python",
        conversation_messages: Optional[list[dict]] = None,
    ) -> GeneratedExercise:
        sys_prompt = "你是一位编程教育专家，擅长出代码修改题。"
        user_prompt = load_prompt("exercise_modification").format(knowledge_point=kp, difficulty=difficulty, language=language)
        messages_with_history, _ = self._build_messages_with_history(sys_prompt, user_prompt, conversation_messages)

        response = await self.llm.chat(
            system_prompt=sys_prompt,
            user_message=user_prompt,
            temperature=0.85 if messages_with_history else 0.7,
            max_tokens=3000,
            messages=messages_with_history,
        )
        data = self._parse_json(response)
        return GeneratedExercise(
            exercise_id=exercise_id,
            exercise_type=ExerciseType.MODIFICATION,
            question=data.get("question", ""),
            starter_code=data.get("starter_code", ""),
            reference_solution=data.get("reference_solution", ""),
            test_cases=data.get("test_cases", ""),
            modification_requirement=data.get("modification_requirement", ""),
            difficulty=difficulty,
            knowledge_points=[kp],
            language=language,
        )

    async def _generate_creation(
        self, exercise_id: str, kp: str, difficulty: str,
        language: str = "python",
        conversation_messages: Optional[list[dict]] = None,
    ) -> GeneratedExercise:
        sys_prompt = "你是一位编程教育专家，擅长出代码创作题。"
        user_prompt = load_prompt("exercise_creation").format(knowledge_point=kp, difficulty=difficulty, language=language)
        messages_with_history, _ = self._build_messages_with_history(sys_prompt, user_prompt, conversation_messages)

        response = await self.llm.chat(
            system_prompt=sys_prompt,
            user_message=user_prompt,
            temperature=0.85 if messages_with_history else 0.7,
            max_tokens=3000,
            messages=messages_with_history,
        )
        data = self._parse_json(response)
        return GeneratedExercise(
            exercise_id=exercise_id,
            exercise_type=ExerciseType.CREATION,
            question=data.get("question", ""),
            starter_code=data.get("starter_code", ""),
            reference_solution=data.get("reference_solution", ""),
            test_cases=data.get("test_cases", ""),
            difficulty=difficulty,
            knowledge_points=[kp],
            language=language,
        )

    async def _generate_project(
        self, exercise_id: str, kp: str, difficulty: str,
        language: str = "python",
        conversation_messages: Optional[list[dict]] = None,
    ) -> GeneratedExercise:
        sys_prompt = "你是一位编程教育专家，擅长出综合项目题。"
        user_prompt = load_prompt("exercise_project").format(knowledge_point=kp, difficulty=difficulty, language=language)
        messages_with_history, _ = self._build_messages_with_history(sys_prompt, user_prompt, conversation_messages)

        response = await self.llm.chat(
            system_prompt=sys_prompt,
            user_message=user_prompt,
            temperature=0.85 if messages_with_history else 0.7,
            max_tokens=4000,
            messages=messages_with_history,
        )
        data = self._parse_json(response)
        return GeneratedExercise(
            exercise_id=exercise_id,
            exercise_type=ExerciseType.PROJECT,
            question=data.get("question", ""),
            starter_code=data.get("starter_code", ""),
            reference_solution=data.get("reference_solution", ""),
            test_cases=data.get("test_cases", ""),
            acceptance_criteria=data.get("acceptance_criteria", []),
            evaluation_dimensions=data.get("evaluation_dimensions", ["功能正确性", "代码结构", "边界处理", "代码质量"]),
            difficulty=difficulty,
            knowledge_points=[kp],
            language=language,
        )

    def _fallback_exercise(
        self,
        exercise_id: str,
        et: ExerciseType,
        kp: str,
        difficulty: str,
        subtype: Optional[str],
        language: str = "python",
    ) -> GeneratedExercise:
        """Generate a simple fallback exercise when LLM is unavailable."""
        if et == ExerciseType.UNDERSTANDING:
            return GeneratedExercise(
                exercise_id=exercise_id,
                exercise_type=et,
                subtype=subtype or "choice",
                question=f"**关于 {kp} 的选择题**\n\n以下哪项最能描述 {kp} 的核心概念？\n\n（Mock 模式：请配置 LLM 以获取真实题目）",
                options=["A. 概念一", "B. 概念二", "C. 概念三", "D. 概念四"],
                correct_answer="A",
                explanation=f"Mock 模式下无法生成详细解析。配置 LLM 后将获得针对 {kp} 的真实题目。",
                difficulty=difficulty,
                knowledge_points=[kp],
                language=language,
            )
        return GeneratedExercise(
            exercise_id=exercise_id,
            exercise_type=et,
            question=f"**关于 {kp} 的{et.value}题**\n\n（Mock 模式：请配置 LLM 以获取真实题目）",
            starter_code="# 请配置 LLM 以获取真实题目\npass\n",
            reference_solution="# 参考答案\npass\n",
            test_cases="# 测试用例\ndef test_placeholder():\n    assert True\n",
            difficulty=difficulty,
            knowledge_points=[kp],
            language=language,
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Parse LLM response as JSON, with markdown code block cleanup."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}
