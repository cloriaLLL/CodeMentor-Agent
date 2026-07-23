"""CodeMentor Agent — 通用简易编译器内核。

本包提供一套可插拔的编译器工具链，用于将自定义教学语言（如 MiniLang）
编译为目标语言（如 Python 源码），并复用现有沙箱引擎安全执行。

设计要点：
- 纯 Python 实现，无外部依赖（仅用标准库 re / dataclasses / hashlib / functools）
- 词法分析：规则表驱动 + 合并正则优化（O(n) 单遍扫描）
- 语法分析：递归下降（语句）+ Pratt parser（表达式）+ panic mode 错误恢复
- 代码生成：AST → Python 源码直通（复用 PythonRuntime，零额外运行时）
- 安全：四层纵深防御（输入验证 → AST 白名单 → 编译沙箱 → 产物二次校验）

模块依赖（无循环）：
    lang ──→ lexer ──→ parser ──→ ast_nodes
                  │        │
                  └─→ compiler_security
                            │
            codegen ←───────┘
                │
        compile_cache / compile_sandbox
                │
        compiler（编排）
                │
   app/services/compiler_service + agents/sandbox_runtime

依据：docs/specs/DOC-05-Compiler_Integration.md
"""
from __future__ import annotations

from compiler.diagnostics import Diagnostic, DiagnosticSeverity, CompileError
from compiler.ast_nodes import (
    Node, Program, NumberLit, StringLit, BooleanLit, VarDecl, VarRef,
    Assign, BinaryOp, UnaryOp, Call, FuncDecl, If, While, Block, Return,
    ExprStmt, Param,
)
from compiler.compiler import compile_source, CompileResult

__all__ = [
    # 诊断
    "Diagnostic", "DiagnosticSeverity", "CompileError",
    # AST 节点
    "Node", "Program", "NumberLit", "StringLit", "BooleanLit",
    "VarDecl", "VarRef", "Assign", "BinaryOp", "UnaryOp", "Call",
    "FuncDecl", "If", "While", "Block", "Return", "ExprStmt", "Param",
    # 编译入口
    "compile_source", "CompileResult",
]

__version__ = "1.0.0"
