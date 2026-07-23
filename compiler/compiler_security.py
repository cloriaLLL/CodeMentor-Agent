"""CodeMentor Agent — AST 级安全校验（安全第二层）。

核心安全增强：相比 sandbox_security.py 的正则黑名单，AST 校验能识别
正则无法捕捉的语义攻击：

1. 字符串拼接构造危险调用：__import__('o'+'s')
2. 动态属性访问：getattr(os, 'system')
3. 禁止白名单外的函数调用
4. 限制循环/递归复杂度（防死循环/资源耗尽）

双校验：AST 校验通过后，编译产物（Python 源码）仍经
validate_code_safety(产物, "python") 二次正则校验。

依据：DOC-05 §5.2 AST 白名单
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from compiler.ast_nodes import (
    Node, Program, Block, NumberLit, StringLit, BooleanLit, VarDecl, VarRef,
    Assign, BinaryOp, UnaryOp, Call, FuncDecl, If, While, Return, ExprStmt, Param,
)
from compiler.diagnostics import (
    Diagnostic, DiagnosticSeverity, ErrorCode, friendly_message,
)


class CompilerSecurityError(Exception):
    """AST 安全校验失败。携带位置信息便于诊断。"""
    def __init__(self, message: str, line: int = 0, column: int = 0,
                 error_code: str = ErrorCode.SEC_FORBIDDEN_CALL):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.error_code = error_code

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            line=self.line, column=self.column,
            message=self.message,
            severity=DiagnosticSeverity.ERROR,
            error_code=self.error_code,
        )


@dataclass
class SecuritySettings:
    """安全校验配置。"""
    # 允许的 AST 节点类型白名单
    allowed_nodes: Optional[set[str]] = None

    # 允许调用的函数白名单（其余调用一律拒绝）
    allowed_calls: Optional[set[str]] = None

    # 禁止的标识符模式（正则；匹配则拒绝）
    forbidden_ident_pattern: Optional[re.Pattern] = None

    # 循环体最大语句数（防死循环构造资源耗尽）
    max_loop_body_size: int = 200

    # AST 最大嵌套深度（防栈溢出攻击）
    max_ast_depth: int = 64

    # 函数参数最大数量
    max_call_args: int = 32

    def __post_init__(self) -> None:
        if self.allowed_nodes is None:
            self.allowed_nodes = _DEFAULT_ALLOWED_NODES
        if self.allowed_calls is None:
            self.allowed_calls = _DEFAULT_ALLOWED_CALLS
        if self.forbidden_ident_pattern is None:
            self.forbidden_ident_pattern = _DEFAULT_FORBIDDEN_IDENT


# 默认白名单（MiniLang 节点全集）
_DEFAULT_ALLOWED_NODES: set[str] = {
    "Node", "Program", "Block", "NumberLit", "StringLit", "BooleanLit",
    "VarDecl", "VarRef", "Assign", "BinaryOp", "UnaryOp", "Call",
    "FuncDecl", "If", "While", "Return", "ExprStmt", "Param",
}

# 允许调用的函数白名单（防代码注入核心）
# 仅教学所需的安全内建函数
_DEFAULT_ALLOWED_CALLS: set[str] = {
    "print", "len", "range", "abs", "min", "max",
    "str", "int", "float", "bool",
    "round", "sum",
}

# 禁止的标识符模式（补充正则黑名单）
# - 双下划线前后缀：__import__ / __builtins__ 等
# - 危险模块名：os / subprocess / sys / shutil / socket / eval / exec / compile / open
_DEFAULT_FORBIDDEN_IDENT = re.compile(
    r"^__\w+__$"           # 双下划线前后缀（dunder）
    r"|^os$|^subprocess$|^sys$|^shutil$|^socket$"   # 危险模块名
    r"|^eval$|^exec$|^compile$|^open$|^input$"      # 危险内建
    r"|^getattr$|^setattr$|^delattr$|^globals$|^locals$"  # 动态访问
    r"|^__import__$|^__builtins__$"                 # 导入相关
)


def check_ast_safety(ast: Program, settings: SecuritySettings | None = None) -> None:
    """遍历 AST，校验所有节点与调用都在白名单内。

    不通过抛 CompilerSecurityError。本函数在编译器内核中调用，
    也可被 compiler_service 单独调用（在缓存命中前的预检阶段）。

    调用白名单策略（两段式）：
    1. 收集所有用户定义的函数名（func 声明）
    2. 调用检查：若 callee 在用户函数表 → 允许（用户自定义函数安全）
                   若 callee 在 ALLOWED_CALLS → 允许（白名单内建）
                   否则 → 拒绝（防 __import__ / eval 等危险调用）
    这样既允许用户函数调用，又拦截危险内建与未知调用。
    """
    if settings is None:
        settings = SecuritySettings()

    # 预扫描：收集用户定义的函数名（允许调用）
    user_funcs = _collect_user_functions(ast, settings.max_ast_depth)

    for node in _walk_with_depth(ast, 0, settings.max_ast_depth):
        # 1. 节点类型白名单
        node_type = type(node).__name__
        if node_type not in settings.allowed_nodes:
            raise CompilerSecurityError(
                friendly_message(
                    ErrorCode.SEC_FORBIDDEN_NODE,
                    line=node.line, node_type=node_type,
                ),
                line=node.line, column=node.column,
                error_code=ErrorCode.SEC_FORBIDDEN_NODE,
            )

        # 2. 函数调用白名单（防代码注入核心）
        if isinstance(node, Call):
            # 用户自定义函数 → 允许
            if node.callee in user_funcs:
                pass   # 允许用户函数调用
            # 内建白名单 → 允许
            elif node.callee in settings.allowed_calls:
                pass
            # 否则 → 拒绝（拦截 __import__ / eval / getattr 等危险调用）
            else:
                raise CompilerSecurityError(
                    friendly_message(ErrorCode.SEC_FORBIDDEN_CALL,
                                     line=node.line, name=node.callee),
                    line=node.line, column=node.column,
                    error_code=ErrorCode.SEC_FORBIDDEN_CALL,
                )
            # 参数数量限制
            if len(node.args) > settings.max_call_args:
                raise CompilerSecurityError(
                    f"第 {node.line} 行：函数调用参数过多（{len(node.args)}），"
                    f"上限 {settings.max_call_args}",
                    line=node.line, column=node.column,
                    error_code=ErrorCode.SEC_FORBIDDEN_CALL,
                )

        # 3. 标识符黑名单（防危险模块/dunder 访问）
        name = getattr(node, "name", None)
        if name and isinstance(name, str):
            if settings.forbidden_ident_pattern.search(name):
                raise CompilerSecurityError(
                    friendly_message(ErrorCode.SEC_FORBIDDEN_IDENT,
                                     line=node.line, name=name),
                    line=node.line, column=node.column,
                    error_code=ErrorCode.SEC_FORBIDDEN_IDENT,
                )

        # 4. 循环复杂度限制（防死循环构造资源耗尽）
        if isinstance(node, While):
            _check_loop_complexity(node, settings)


def _collect_user_functions(ast: Program, max_depth: int = 256) -> set[str]:
    """预扫描 AST，收集所有用户定义的函数名。

    这些函数的调用应被允许（用户代码内的函数调用是安全的，
    真正需要拦截的是 __import__ / eval / getattr 等危险内建）。
    """
    funcs: set[str] = set()
    for node in _walk_with_depth(ast, 0, max_depth):
        if isinstance(node, FuncDecl):
            funcs.add(node.name)
    return funcs


def _walk_with_depth(node: Node, depth: int, max_depth: int):
    """带深度限制的 AST 遍历生成器。

    防止恶意构造的深层 AST 导致递归栈溢出。
    """
    if depth > max_depth:
        raise CompilerSecurityError(
            f"AST 深度 {depth} 超过上限 {max_depth}，可能为栈溢出攻击",
            line=getattr(node, "line", 0),
            error_code=ErrorCode.SEC_LOOP_TOO_COMPLEX,
        )
    yield node
    for child in _children(node):
        yield from _walk_with_depth(child, depth + 1, max_depth)


def _children(node: Node) -> list[Node]:
    """获取节点的直接子节点。"""
    children: list[Node] = []
    if isinstance(node, Program):
        children.extend(node.statements)
    elif isinstance(node, Block):
        children.extend(node.statements)
    elif isinstance(node, (VarDecl, Assign)):
        if node.value is not None:
            children.append(node.value)
    elif isinstance(node, BinaryOp):
        if node.left is not None:
            children.append(node.left)
        if node.right is not None:
            children.append(node.right)
    elif isinstance(node, UnaryOp):
        if node.operand is not None:
            children.append(node.operand)
    elif isinstance(node, Call):
        children.extend(node.args)
    elif isinstance(node, FuncDecl):
        children.extend(node.params)
        if node.body is not None:
            children.append(node.body)
    elif isinstance(node, If):
        if node.condition is not None:
            children.append(node.condition)
        if node.then_body is not None:
            children.append(node.then_body)
        if node.else_body is not None:
            children.append(node.else_body)
    elif isinstance(node, While):
        if node.condition is not None:
            children.append(node.condition)
        if node.body is not None:
            children.append(node.body)
    elif isinstance(node, Return):
        if node.value is not None:
            children.append(node.value)
    elif isinstance(node, ExprStmt):
        if node.expr is not None:
            children.append(node.expr)
    return children


def _check_loop_complexity(node: While, settings: SecuritySettings) -> None:
    """检查循环体复杂度。

    防止构造超大循环体导致生成的 Python 代码运行时资源耗尽。
    """
    if node.body is None:
        return
    stmt_count = len(node.body.statements)
    if stmt_count > settings.max_loop_body_size:
        raise CompilerSecurityError(
            friendly_message(ErrorCode.SEC_LOOP_TOO_COMPLEX, line=node.line),
            line=node.line, column=node.column,
            error_code=ErrorCode.SEC_LOOP_TOO_COMPLEX,
        )
