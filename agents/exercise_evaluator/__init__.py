"""CodeMentor Agent - 多题型练习评估器子包。

从原 922 行 God Class (agents/exercise_evaluator.py) 拆分为：
- models.py:      EvaluationResult Pydantic 模型
- quality.py:     CodeQualityAssessor 纯函数代码质量评分
- ai_feedback.py: AIFeedbackBuilder LLM 反馈生成
- core.py:        ExerciseEvaluator 路由 + 沙箱编排（组合上述两类）

公开 API 向后兼容：`from agents.exercise_evaluator import ExerciseEvaluator` 签名不变。
"""
from agents.exercise_evaluator.ai_feedback import AIFeedbackBuilder
from agents.exercise_evaluator.core import ExerciseEvaluator
from agents.exercise_evaluator.models import EvaluationResult
from agents.exercise_evaluator.quality import CodeQualityAssessor

__all__ = ["EvaluationResult", "ExerciseEvaluator", "CodeQualityAssessor", "AIFeedbackBuilder"]
