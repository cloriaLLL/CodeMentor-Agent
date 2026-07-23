"""CodeMentor Agent — 诊断服务。

复用编译器的词法/语法分析，提供一次性诊断（panic mode 错误恢复
保证一次编译返回所有错误，IDE 无需多次编译）。

诊断分为：
- error：词法/语法错误（阻塞编译）
- warning：可能的问题（如缺少分号）
- info：建议性信息

性能预算：< 100ms（防抖后）。

依据：DOC-05 §4.3 一次性诊断
"""
from __future__ import annotations

from compiler import compile_source
from compiler.diagnostics import Diagnostic


def lint(source: str, language: str = "minilang") -> list[Diagnostic]:
    """对源码执行诊断，返回所有诊断信息。

    本函数是 compile_source 的诊断提取封装，跳过代码生成（仅前端分析），
    提升性能。返回的 Diagnostic 列表可直接用于前端下划线渲染。
    """
    # 使用 compile_source 但只取 diagnostics（复用缓存）
    result = compile_source(source, language=language, target="python", return_ast=False)
    return result.diagnostics


def lint_to_dict(source: str, language: str = "minilang") -> list[dict]:
    """诊断并返回 JSON 友好的字典列表（供 API 响应）。"""
    diags = lint(source, language)
    return [d.to_dict() for d in diags]
