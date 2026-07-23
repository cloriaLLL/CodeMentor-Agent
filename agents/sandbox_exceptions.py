"""CodeMentor Agent — 沙箱异常定义集中模块。

将异常类从 sandbox.py 抽离，打破 sandbox ↔ sandbox_security ↔ sandbox_runtime
之间的循环依赖。sandbox.py 仍 re-export 这些异常以保持向后兼容
（保护 practice.py、exercise_evaluator.py 等现有 `from agents.sandbox import ...`）。
"""
from __future__ import annotations


class SandboxError(Exception):
    """沙盒执行基础异常"""


class SecurityViolationError(SandboxError):
    """代码安全检查未通过"""


class SandboxTimeoutError(SandboxError):
    """执行超时"""


class ExecutionError(SandboxError):
    """执行异常（运行时不可用、编译失败等）"""


class UnsupportedLanguageError(SandboxError):
    """不支持的语言（未在运行时注册表中注册）"""


__all__ = [
    "SandboxError",
    "SecurityViolationError",
    "SandboxTimeoutError",
    "ExecutionError",
    "UnsupportedLanguageError",
]
