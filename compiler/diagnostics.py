"""CodeMentor Agent — 编译器诊断信息模型。

诊断（Diagnostic）贯穿词法/语法/代码生成全流程，统一格式：
- 携带源码位置（line/column/end_column）供 IDE 精确高亮
- severity 区分 error/warning/info
- error_code 供前端本地化与统计

错误恢复策略：词法与语法分析遇错不立即终止，而是记录诊断后继续
（panic mode 同步到下一语句边界），保证一次编译产出尽可能多的诊断
信息——这是 IDE 实时诊断的关键。

依据：DOC-05 §4.3 一次性诊断
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DiagnosticSeverity(str, Enum):
    """诊断严重级别。继承 str 便于 JSON 序列化。"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass(frozen=True)
class Diagnostic:
    """单条诊断信息。

    line/column 基于 1（与主流 IDE 一致），end_column 为错误范围的
    结束列（用于波浪线高亮），可为 None 表示单点。
    """
    line: int
    column: int
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    end_column: Optional[int] = None
    error_code: str = ""

    def to_dict(self) -> dict:
        """序列化为 JSON 友好的字典（供 API 响应）。"""
        return {
            "line": self.line,
            "column": self.column,
            "end_column": self.end_column,
            "message": self.message,
            "severity": self.severity.value,
            "error_code": self.error_code,
        }


class CompileError(Exception):
    """编译期错误（不可恢复，终止编译）。

    用于输入验证失败、安全校验拦截等硬性错误。
    语法错误不抛此异常，而是记录为 Diagnostic 继续编译。
    """

    def __init__(self, message: str, line: int = 0, column: int = 0,
                 error_code: str = "E_COMPILE"):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.error_code = error_code

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            line=self.line,
            column=self.column,
            message=self.message,
            severity=DiagnosticSeverity.ERROR,
            error_code=self.error_code,
        )


# --------------------------------------------------------------------------- #
# 错误码常量（供前端本地化与统计）
# --------------------------------------------------------------------------- #

class ErrorCode:
    # 词法错误
    LEX_UNEXPECTED_CHAR = "E_LEX_UNEXPECTED_CHAR"

    # 语法错误
    SYN_UNEXPECTED_TOKEN = "E_SYN_UNEXPECTED_TOKEN"
    SYN_EXPECTED_TOKEN = "E_SYN_EXPECTED_TOKEN"
    SYN_UNTERMINATED_STRING = "E_SYN_UNTERMINATED_STRING"
    SYN_EMPTY_INPUT = "E_SYN_EMPTY_INPUT"

    # 输入验证
    VAL_TOO_LONG = "E_VAL_TOO_LONG"
    VAL_NESTING_TOO_DEEP = "E_VAL_NESTING_TOO_DEEP"
    VAL_UNBALANCED_BRACKETS = "E_VAL_UNBALANCED_BRACKETS"
    VAL_ILLEGAL_CHAR = "E_VAL_ILLEGAL_CHAR"

    # 安全校验
    SEC_FORBIDDEN_NODE = "E_SEC_FORBIDDEN_NODE"
    SEC_FORBIDDEN_CALL = "E_SEC_FORBIDDEN_CALL"
    SEC_FORBIDDEN_IDENT = "E_SEC_FORBIDDEN_IDENT"
    SEC_LOOP_TOO_COMPLEX = "E_SEC_LOOP_TOO_COMPLEX"

    # 代码生成
    CG_UNSUPPORTED_NODE = "E_CG_UNSUPPORTED_NODE"

    # 编译沙箱
    SB_COMPILE_TIMEOUT = "E_SB_COMPILE_TIMEOUT"
    SB_RECURSION_LIMIT = "E_SB_RECURSION_LIMIT"


# 错误码 → 友好提示模板（模块级，避免每次调用重建）
templates: dict[str, str] = {
    ErrorCode.LEX_UNEXPECTED_CHAR:
        "第 {line} 行：非法字符 {char!r}，请检查输入是否正确。",
    ErrorCode.SYN_UNEXPECTED_TOKEN:
        "第 {line} 行：意外的标记 '{token}'。请检查语法是否正确。",
    ErrorCode.SYN_EXPECTED_TOKEN:
        "第 {line} 行：期望 '{expected}' 但遇到 '{actual}'。",
    ErrorCode.SYN_UNTERMINATED_STRING:
        "第 {line} 行：字符串未闭合，缺少结束引号。",
    ErrorCode.VAL_TOO_LONG:
        "源码过长（{length} 字符），超过上限 {max_length}。",
    ErrorCode.VAL_NESTING_TOO_DEEP:
        "嵌套深度 {depth} 超过上限 {max_depth}，可能为栈溢出攻击。",
    ErrorCode.VAL_UNBALANCED_BRACKETS:
        "括号不匹配，请检查 ( ) [ ] {{ }} 是否成对。",
    ErrorCode.VAL_ILLEGAL_CHAR:
        "第 {line} 行：含非法控制字符 U+{code:04X}。",
    ErrorCode.SEC_FORBIDDEN_NODE:
        "第 {line} 行：禁止的语法结构 {node_type}。",
    ErrorCode.SEC_FORBIDDEN_CALL:
        "第 {line} 行：禁止调用函数 '{name}'，仅允许白名单内建函数。",
    ErrorCode.SEC_FORBIDDEN_IDENT:
        "第 {line} 行：禁止的标识符 '{name}'。",
    ErrorCode.SEC_LOOP_TOO_COMPLEX:
        "第 {line} 行：循环体过于复杂，可能造成资源耗尽。",
}


def friendly_message(error_code: str, **kwargs) -> str:
    """根据错误码生成教学友好的中文提示。

    教学场景下，错误提示需可读且带引导，而非晦涩的技术术语。
    若 kwargs 缺少模板占位符，回退到通用消息，避免二次 KeyError。
    """
    fallback = "编译错误：{detail}"
    tpl = templates.get(error_code, fallback)
    try:
        return tpl.format(**kwargs)
    except (KeyError, IndexError):
        # 模板占位符缺失时回退到通用消息，而非抛出二次异常
        return fallback.format(detail=kwargs.get("detail", error_code))
