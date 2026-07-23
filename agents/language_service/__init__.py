"""CodeMentor Agent — IDE 语言服务包。

复用编译器前端（Lexer + Parser）提供 IDE 能力：
- completion：自动补全
- diagnostics_service：错误诊断
- hover：悬停提示与签名帮助

这是自研编译器相比调外部 LSP 的核心优势——前端分析能力天然支持 IDE。

依据：DOC-05 §4 IDE 语言服务设计
"""
from __future__ import annotations

from compiler.lang import get_spec
from compiler.lang.language_spec import LanguageSpec
from compiler.lexer import Lexer
from compiler.parser import Parser

from agents.language_service.completion import (
    CompletionItem, CompletionKind, complete,
)
from agents.language_service.diagnostics_service import lint
from agents.language_service.hover import (
    HoverResult, SignatureHelp, SignatureInfo, ParameterInfo, hover, signature_help,
)
from agents.language_service.language_service import LanguageService


__all__ = [
    "CompletionItem", "CompletionKind", "complete",
    "lint",
    "HoverResult", "SignatureHelp", "SignatureInfo", "ParameterInfo",
    "hover", "signature_help",
    "LanguageService",
]
