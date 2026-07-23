"""CodeMentor Agent — 编译流水线编排。

整合词法分析、语法分析、代码生成、缓存，提供统一的编译入口。

流水线：
    源码 → Lexer.tokenize → Parser.parse → Codegen.emit → 目标代码
                                  ↓
                              diagnostics（贯穿全流程）

缓存：编译前查 cache，命中则跳过全流程直接返回。
（输入验证与 AST 安全校验由 compiler_service / compile_sandbox 调用，
本模块仅负责纯编译，保持单一职责。）

依据：DOC-05 §2.1 编译器内核对外接口
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from compiler.ast_nodes import Program
from compiler.codegen import get_codegen
from compiler.compile_cache import cache_key, get_cache
from compiler.diagnostics import Diagnostic, DiagnosticSeverity, ErrorCode
from compiler.lang import get_spec
from compiler.lexer import Lexer
from compiler.parser import Parser


@dataclass
class CompileResult:
    """编译结果。"""
    target_code: str
    diagnostics: list[Diagnostic] = field(default_factory=list)
    ast: Optional[Program] = None
    elapsed_sec: float = 0.0
    from_cache: bool = False
    language: str = ""
    target: str = ""

    @property
    def has_error(self) -> bool:
        """是否存在错误级诊断。"""
        return any(d.severity == "error" for d in self.diagnostics)

    def to_dict(self) -> dict:
        return {
            "target_code": self.target_code,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "elapsed_sec": round(self.elapsed_sec, 4),
            "from_cache": self.from_cache,
            "has_error": self.has_error,
            "language": self.language,
            "target": self.target,
        }


def compile_source(
    source: str,
    language: str = "minilang",
    target: str = "python",
    *,
    skip_cache: bool = False,
    return_ast: bool = True,
) -> CompileResult:
    """编译源代码到目标语言。

    参数：
        source: 源代码字符串
        language: 源语言名（需在 lang 注册表中）
        target: 目标语言（python / bytecode）
        skip_cache: 跳过缓存（强制重新编译）
        return_ast: 是否在结果中附带 AST（IDE 服务需要，纯编译可关闭以省内存）

    返回 CompileResult。若编译期有错误，diagnostics 会包含错误信息，
    target_code 可能为空或部分产物（取决于错误严重性）。

    本函数不抛异常，所有错误以 Diagnostic 形式返回，
    便于 IDE 一次性展示所有问题。
    """
    start = time.perf_counter()
    try:
        spec = get_spec(language)
    except Exception as e:
        return CompileResult(
            target_code="",
            diagnostics=[Diagnostic(
                line=0, column=0,
                message=f"语言未注册或加载失败: {e}",
                severity=DiagnosticSeverity.ERROR,
                error_code=ErrorCode.LEX_UNKNOWN_TOKEN,
            )],
            ast=None,
            elapsed_sec=time.perf_counter() - start,
            from_cache=False,
            language=language,
            target=target,
        )
    cache = get_cache()

    # 缓存查询
    ckey = cache_key(language, source, target, spec.spec_version)
    if not skip_cache:
        cached = cache.get(ckey)
        if cached is not None:
            return CompileResult(
                target_code=cached,
                diagnostics=[],
                ast=None,
                elapsed_sec=time.perf_counter() - start,
                from_cache=True,
                language=language,
                target=target,
            )

    # 词法分析
    lexer = Lexer(spec)
    tokens, lex_diagnostics = lexer.tokenize(source)

    # 语法分析
    parser = Parser(spec, tokens)
    ast, parse_diagnostics = parser.parse()

    all_diagnostics = list(lex_diagnostics) + list(parse_diagnostics)

    # 若有词法/语法错误，不进行代码生成
    if any(d.severity == DiagnosticSeverity.ERROR for d in all_diagnostics):
        return CompileResult(
            target_code="",
            diagnostics=all_diagnostics,
            ast=ast if return_ast else None,
            elapsed_sec=time.perf_counter() - start,
            from_cache=False,
            language=language,
            target=target,
        )

    # 代码生成
    try:
        codegen = get_codegen(target)
        target_code = codegen.emit(ast)
    except Exception as e:
        line = getattr(e, "line", 0)
        column = getattr(e, "column", 0)
        all_diagnostics.append(Diagnostic(
            line=line, column=column,
            message=f"代码生成失败: {e}",
            severity=DiagnosticSeverity.ERROR,
            error_code=getattr(e, "error_code", ErrorCode.CG_UNSUPPORTED_NODE),
        ))
        return CompileResult(
            target_code="",
            diagnostics=all_diagnostics,
            ast=ast if return_ast else None,
            elapsed_sec=time.perf_counter() - start,
            from_cache=False,
            language=language,
            target=target,
        )

    # 写入缓存
    cache.set(ckey, target_code)

    return CompileResult(
        target_code=target_code,
        diagnostics=all_diagnostics,
        ast=ast if return_ast else None,
        elapsed_sec=time.perf_counter() - start,
        from_cache=False,
        language=language,
        target=target,
    )
