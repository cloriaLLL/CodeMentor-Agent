"""CodeMentor Agent — 编译器语言规范层。

每个语言（MiniLang 等）实现 LanguageSpec，声明：
- 关键字、内建函数、运算符优先级
- 词法规则（TokenRule 列表）
- 规范版本（SPEC_VERSION，变更时缓存自动失效）

规范层是编译器内核与具体语言的解耦点：内核不感知任何具体语法，
所有语法信息由 LanguageSpec 提供。新增语言只需新增 spec 文件。
"""
from __future__ import annotations

from compiler.lang.language_spec import (
    LanguageSpec, TokenRule, OperatorPrec,
)
from compiler.lang.minilang import MiniLangSpec

# 语言注册表：language name → spec 实例
_REGISTRY: dict[str, LanguageSpec] = {}


def register_spec(spec: LanguageSpec) -> None:
    """注册语言规范（按规范名 + 别名）。"""
    canonical = spec.language.lower()
    _REGISTRY[canonical] = spec
    for alias in spec.aliases:
        _REGISTRY[alias.lower()] = canonical


def get_spec(language: str) -> LanguageSpec:
    """获取语言规范。未注册抛 ValueError。"""
    if not language:
        raise ValueError("language 为空")
    key = language.lower()
    # 别名解析
    if key in _REGISTRY and isinstance(_REGISTRY[key], str):
        key = _REGISTRY[key]
    if key not in _REGISTRY:
        raise ValueError(
            f"未注册的语言规范：{language}。已注册：{sorted(k for k, v in _REGISTRY.items() if not isinstance(v, str))}"
        )
    return _REGISTRY[key]


def list_specs() -> list[LanguageSpec]:
    """返回所有已注册语言规范。"""
    return [v for k, v in _REGISTRY.items() if not isinstance(v, str)]


# 模块加载时注册内置语言
register_spec(MiniLangSpec())

__all__ = [
    "LanguageSpec", "TokenRule", "OperatorPrec",
    "MiniLangSpec",
    "register_spec", "get_spec", "list_specs",
]
