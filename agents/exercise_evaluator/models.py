"""CodeMentor Agent - 评估结果数据模型。

独立出来便于 quality / ai_feedback / core 三模块共享，
且方便外部消费者（exercise_service、API 层）单独 import。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """Result of evaluating a user submission."""

    passed: bool = Field(..., description="是否通过")
    score: int = Field(0, ge=0, le=100, description="得分 0-100")
    result: str = Field(..., description="结果状态: passed/failed/error")
    feedback: str = Field("", description="反馈信息")
    details: dict[str, Any] = Field(default_factory=dict, description="详细评估数据")
    needs_reteach: bool = Field(False, description="是否需要重新讲解")
