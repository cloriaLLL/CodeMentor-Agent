"""CodeMentor Agent - Exercise service layer.

Orchestrates exercise generation, evaluation, and submission tracking.
Acts as the bridge between API endpoints, agents, and learning state.
"""
from __future__ import annotations

import uuid
from typing import Optional

from agents.exercise_evaluator import EvaluationResult, ExerciseEvaluator
from agents.exercise_generator import (
    ExerciseGeneratorAgent,
    ExerciseType,
    GeneratedExercise,
    UnderstandingSubtype,
)
from app.core.logger import get_logger
from app.services.conversation_store import ConversationStore
from app.services.learning_state import LearningStateService

logger = get_logger(__name__)


class ExerciseService:
    """Service for exercise lifecycle management."""

    def __init__(self) -> None:
        self.generator = ExerciseGeneratorAgent()
        self.evaluator = ExerciseEvaluator()
        self.state_service = LearningStateService()
        self.conv_store = ConversationStore()

    async def generate_exercise(
        self,
        exercise_type: str,
        knowledge_point: str,
        difficulty: str = "Medium",
        subtype: Optional[str] = None,
        session_id: Optional[str] = None,
        language: str = "python",
    ) -> tuple[GeneratedExercise, str, str]:
        """Generate an exercise and optionally link it to a session.

        Returns (exercise, conversation_id, module_key).
        Manages per-module conversation so LLM sees prior exercises (anti-repeat).
        """
        try:
            et = ExerciseType(exercise_type)
        except ValueError:
            raise ValueError(f"Unsupported exercise type: {exercise_type}. "
                             f"Supported: {[t.value for t in ExerciseType]}")

        # Compute module key and get/create module conversation
        module_key = self._compute_module_key(language, exercise_type, subtype)
        conv = self.conv_store.get_or_create_module_conversation(
            module_key,
            meta={"language": language, "exercise_type": exercise_type, "subtype": subtype or ""},
        )

        # Load conversation history as LLM context
        conversation_messages = self.conv_store.get_messages_as_llm_history(
            conv.conversation_id, limit=20
        )

        exercise = await self.generator.generate(
            exercise_type=et,
            knowledge_point=knowledge_point,
            difficulty=difficulty,
            subtype=subtype,
            language=language,
            conversation_messages=conversation_messages or None,
        )

        # Ensure unique ID
        exercise.exercise_id = f"{exercise.exercise_id}_{uuid.uuid4().hex[:6]}"

        # Persist to module conversation
        user_msg_summary = (
            f"生成 {exercise_type} 题目: 知识点={knowledge_point}, "
            f"难度={difficulty}, 语言={language}"
            + (f", 子类型={subtype}" if subtype else "")
        )
        self.conv_store.add_message(
            conv.conversation_id, role="user", content=user_msg_summary,
        )
        self.conv_store.add_message(
            conv.conversation_id, role="assistant",
            content=exercise.model_dump_json(),
            msg_meta={"exercise_id": exercise.exercise_id},
        )

        logger.info(
            "exercise_generated",
            exercise_id=exercise.exercise_id,
            type=exercise_type,
            knowledge_point=knowledge_point,
            module_key=module_key,
            conversation_id=conv.conversation_id,
        )
        return exercise, conv.conversation_id, module_key

    @staticmethod
    def _compute_module_key(language: str, exercise_type: str, subtype: Optional[str]) -> str:
        """Compute module key: '{language}:{exercise_type}' + (':{subtype}' if subtype)."""
        key = f"{language}:{exercise_type}"
        if subtype:
            key += f":{subtype}"
        return key

    async def evaluate_submission(
        self,
        exercise: GeneratedExercise,
        user_answer: str,
        session_id: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate a user submission and record it."""
        result = await self.evaluator.evaluate(exercise, user_answer)

        if session_id:
            self.state_service.record_submission(
                session_id=session_id,
                exercise_id=exercise.exercise_id,
                exercise_type=exercise.exercise_type.value,
                user_answer=user_answer,
                result=result.result,
                score=result.score,
                feedback=result.feedback,
                exercise_subtype=exercise.subtype or "",
            )

            # Update learning progress if exercise is related to a knowledge point
            if exercise.knowledge_points:
                kp = exercise.knowledge_points[0]
                current_score = self.state_service.get_mastery_score(session_id, kp)
                # Take the higher score as mastery
                best_score = max(current_score, result.score)
                if result.passed:
                    self.state_service.complete_knowledge_point(
                        session_id, kp, best_score
                    )

        logger.info(
            "exercise_evaluated",
            exercise_id=exercise.exercise_id,
            passed=result.passed,
            score=result.score,
            needs_reteach=result.needs_reteach,
        )
        return result

    def get_supported_types(self) -> list[dict]:
        """Get all supported exercise types and subtypes."""
        return [
            {
                "type": ExerciseType.UNDERSTANDING.value,
                "label": "理解型题目",
                "description": "选择题、判断题、填空题，即时判题",
                "subtypes": [s.value for s in UnderstandingSubtype],
            },
            {
                "type": ExerciseType.MODIFICATION.value,
                "label": "修改型题目",
                "description": "基于已有代码进行针对性修改",
                "subtypes": None,
            },
            {
                "type": ExerciseType.CREATION.value,
                "label": "创作型题目",
                "description": "从零开始编写代码，自动评估",
                "subtypes": None,
            },
            {
                "type": ExerciseType.PROJECT.value,
                "label": "综合项目题",
                "description": "模块级项目，多维度评价",
                "subtypes": None,
            },
        ]
