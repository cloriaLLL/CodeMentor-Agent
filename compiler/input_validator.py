"""CodeMentor Agent — 输入验证（安全第一层）。

编译前对原始输入做约束，防止资源耗尽类攻击：
1. 巨型源码导致词法分析 OOM
2. 深度嵌套导致递归下降解析器栈溢出
3. 超长单行/标识符导致正则灾难
4. 非法字符注入（零宽字符、控制字符）

本层是最早的防御，在词法分析之前执行。配合 AST 白名单（第二层）、
编译沙箱（第三层）、产物二次校验（第四层）形成纵深防御。

依据：DOC-05 §5.1 输入验证
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from compiler.diagnostics import (
    CompileError, ErrorCode, friendly_message,
)


@dataclass
class InputValidationSettings:
    """输入验证配置。可由 app config 注入。"""
    max_source_len: int = 50000          # 源码最大字符数
    max_ast_depth: int = 64              # 最大嵌套深度
    max_line_len: int = 10000             # 单行最大长度
    max_ident_len: int = 256              # 标识符最大长度

    # 允许的 Unicode 类别（Cn 控制字符等会被拒绝）
    # Cc 控制字符中仅允许 \n \t \r
    allowed_categories: tuple[str, ...] = (
        "Lu", "Ll", "Lt", "Lm", "Lo",   # 字母
        "Nd", "Nl", "No",                # 数字
        "Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po",  # 标点
        "Sm", "Sc", "Sk", "So",          # 符号
        "Zs",                             # 空格分隔符
    )


class InputValidationError(CompileError):
    """输入验证失败。"""
    def __init__(self, message: str, error_code: str = ErrorCode.VAL_TOO_LONG,
                 line: int = 0, column: int = 0):
        super().__init__(message, line, column, error_code)


def validate_input(source: str, settings: InputValidationSettings | None = None) -> None:
    """验证原始源码输入。不通过抛 InputValidationError。

    检查项：
    1. 长度限制（防 OOM）
    2. 单行长度限制（防正则灾难）
    3. 嵌套深度预检（防栈溢出）
    4. 控制字符过滤（防注入零宽字符等）
    5. 字符类别白名单
    """
    if settings is None:
        settings = InputValidationSettings()

    if source is None:
        raise InputValidationError("源码为 None", ErrorCode.VAL_TOO_LONG)

    # 1. 长度限制
    if len(source) > settings.max_source_len:
        raise InputValidationError(
            friendly_message(ErrorCode.VAL_TOO_LONG,
                             length=len(source), max_length=settings.max_source_len),
            error_code=ErrorCode.VAL_TOO_LONG,
        )

    # 2. 单行长度限制
    for i, line in enumerate(source.split("\n"), start=1):
        if len(line) > settings.max_line_len:
            raise InputValidationError(
                f"第 {i} 行过长（{len(line)} 字符），超过上限 {settings.max_line_len}",
                error_code=ErrorCode.VAL_TOO_LONG,
                line=i,
            )

    # 3. 嵌套深度预检（括号配对 + 深度）
    _check_nesting_depth(source, settings.max_ast_depth)

    # 4 & 5. 字符类别与控制字符检查
    _check_characters(source, settings)


def _check_nesting_depth(source: str, max_depth: int) -> None:
    """括号配对与嵌套深度检查。

    - 不匹配 → VAL_UNBALANCED_BRACKETS
    - 深度超限 → VAL_NESTING_TOO_DEEP
    - 忽略字符串字面量内的括号
    """
    depth = 0
    line = 1
    col = 0    # 0-based 列号，输出时 +1 转 1-based
    stack: list[tuple[str, int, int]] = []
    pairs = {")": "(", "]": "[", "}": "{"}
    opens = set(pairs.values())
    in_string: str | None = None
    escaped = False

    for ch in source:
        if ch == "\n":
            line += 1
            col = 0
            if in_string:
                in_string = None
                escaped = False
            continue
        col += 1

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            continue

        if ch == '"' or ch == "'":
            in_string = ch
            continue

        if ch in opens:
            depth += 1
            stack.append((ch, line, col))
            if depth > max_depth:
                raise InputValidationError(
                    friendly_message(ErrorCode.VAL_NESTING_TOO_DEEP,
                                     depth=depth, max_depth=max_depth),
                    error_code=ErrorCode.VAL_NESTING_TOO_DEEP,
                    line=line, column=col,
                )
        elif ch in pairs:
            if not stack:
                raise InputValidationError(
                    friendly_message(ErrorCode.VAL_UNBALANCED_BRACKETS),
                    error_code=ErrorCode.VAL_UNBALANCED_BRACKETS,
                    line=line, column=col,
                )
            expected_open = pairs[ch]
            actual_open, _, _ = stack[-1]
            if actual_open != expected_open:
                raise InputValidationError(
                    friendly_message(ErrorCode.VAL_UNBALANCED_BRACKETS),
                    error_code=ErrorCode.VAL_UNBALANCED_BRACKETS,
                    line=line, column=col,
                )
            stack.pop()
            depth -= 1

    if stack:
        ch, ln, cl = stack[-1]
        raise InputValidationError(
            friendly_message(ErrorCode.VAL_UNBALANCED_BRACKETS),
            error_code=ErrorCode.VAL_UNBALANCED_BRACKETS,
            line=ln, column=cl,
        )


def _check_characters(source: str, settings: InputValidationSettings) -> None:
    """字符类别与控制字符检查。

    - 拒绝 Unicode 控制字符（Cc 类别），但允许 \\n \\t \\r
    - 拒绝不常见类别（Cf 格式字符含零宽字符 U+200B 等，Cs 代理对，Co 私用区）
    - 启用字符类别白名单时，拒绝不在白名单中的类别
    """
    allowed_control = {"\n", "\t", "\r"}
    # 预计算换行位置，用增量更新避免 O(n²)
    line = 1
    for i, ch in enumerate(source):
        if ch == "\n":
            line += 1
            continue
        if ch in allowed_control:
            continue
        category = unicodedata.category(ch)
        # C* 类别全部拒绝（控制/格式/代理/私用/未分配）
        if category.startswith("C"):
            # 列号 = 当前位置 - 上一换行位置
            last_nl = source.rfind("\n", 0, i)
            col = i - last_nl if last_nl >= 0 else i + 1
            raise InputValidationError(
                friendly_message(ErrorCode.VAL_ILLEGAL_CHAR, line=line, code=ord(ch)),
                error_code=ErrorCode.VAL_ILLEGAL_CHAR,
                line=line, column=col,
            )
        # 字符类别白名单检查（若启用）
        if settings.allowed_categories and category not in settings.allowed_categories:
            last_nl = source.rfind("\n", 0, i)
            col = i - last_nl if last_nl >= 0 else i + 1
            raise InputValidationError(
                f"第 {line} 行：字符 {ch!r}（类别 {category}）不在允许的字符集内",
                error_code=ErrorCode.VAL_ILLEGAL_CHAR,
                line=line, column=col,
            )
