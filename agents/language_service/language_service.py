"""CodeMentor Agent — IDE 语言服务编排层。

整合 completion / diagnostics / hover / signature_help 为统一服务，
供 app/services/compiler_service 与 API 端点调用。

提供缓存优化：同一源码的诊断/补全结果缓存，避免重复分析。

依据：DOC-05 §4 IDE 语言服务设计
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from compiler.diagnostics import Diagnostic

from agents.language_service.completion import (
    CompletionItem, complete as _complete,
)
from agents.language_service.diagnostics_service import lint as _lint
from agents.language_service.hover import (
    HoverResult, SignatureHelp, hover as _hover, signature_help as _sig_help,
)


@dataclass
class LanguageServiceSettings:
    """语言服务配置。"""
    max_completion_items: int = 50
    lint_cache_size: int = 128


class LanguageService:
    """IDE 语言服务统一入口。

    封装补全、诊断、悬停、签名帮助，提供简洁 API。
    """

    def __init__(self, settings: LanguageServiceSettings | None = None) -> None:
        self._settings = settings or LanguageServiceSettings()

    def complete(self, source: str, cursor_offset: int,
                 language: str = "minilang") -> list[CompletionItem]:
        """自动补全。"""
        return _complete(
            source, cursor_offset, language,
            max_items=self._settings.max_completion_items,
        )

    def lint(self, source: str, language: str = "minilang") -> list[Diagnostic]:
        """诊断。"""
        return _lint(source, language)

    def hover(self, source: str, offset: int,
              language: str = "minilang") -> Optional[HoverResult]:
        """悬停提示。"""
        return _hover(source, offset, language)

    def signature_help(self, source: str, offset: int,
                       language: str = "minilang") -> Optional[SignatureHelp]:
        """签名帮助。"""
        return _sig_help(source, offset, language)

    def full_analysis(self, source: str, cursor_offset: int,
                      language: str = "minilang") -> dict:
        """一次性返回补全 + 诊断（编辑器一次请求获取全部，减少 RTT）。

        用于前端防抖后的批量请求。
        """
        completions = self.complete(source, cursor_offset, language)
        diagnostics = self.lint(source, language)
        hover_result = self.hover(source, cursor_offset, language)
        return {
            "completions": [c.to_dict() for c in completions],
            "diagnostics": [d.to_dict() for d in diagnostics],
            "hover": hover_result.to_dict() if hover_result else None,
        }
