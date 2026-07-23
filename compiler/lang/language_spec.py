"""CodeMentor Agent — 语言规范基类与词法规则定义。

LanguageSpec 声明一门语言的所有静态信息；TokenRule 描述单个词法规则。
Lexer 根据 spec 构造合并正则，Parser 根据 spec 的运算符优先级表解析表达式。

依据：DOC-05 §3.1 规则表驱动词法分析
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class TokenType(Enum):
    """通用 token 类型。各语言可扩展子类型，但核心类型保持一致。"""
    NUMBER = "number"
    STRING = "string"
    IDENT = "ident"
    KEYWORD = "keyword"
    OP = "operator"          # 运算符：+ - * / == != < > = 等
    PUNCT = "punctuation"    # 标点：( ) { } , ; 等
    NEWLINE = "newline"
    EOF = "eof"
    ERROR = "error"


@dataclass(frozen=True)
class Token:
    """词法 token。携带源码位置，供 IDE 诊断与解析器错误定位。

    frozen=True 使 token 可哈希，便于缓存与等值比较。
    """
    type: TokenType
    value: str
    line: int
    column: int
    offset: int          # 全局偏移，便于 IDE 按字符定位


@dataclass
class TokenRule:
    """单条词法规则。

    pattern: 正则字符串（不含命名组，由 Lexer 统一包装）
    token_type: 匹配成功后赋予的 token 类型
    priority: 越大越优先（关键字优先于标识符，避免 'if' 被识别为标识符）
    callback: 可选后处理，返回 (TokenType, value) 或 None（跳过该 token）
    """
    name: str
    pattern: str
    token_type: TokenType
    priority: int = 0
    callback: Optional[Callable[[str], Optional[tuple[TokenType, str]]]] = None


# 运算符优先级表：op → precedence（越大越优先）
# Pratt parser 据此决定运算符结合方式
OperatorPrec = dict[str, int]


@dataclass
class LanguageSpec:
    """语言规范基类。子类填充类属性声明语言元数据。"""
    language: str = ""
    aliases: tuple[str, ...] = ()
    display_name: str = ""
    spec_version: str = "1.0"        # 变更时编译缓存自动失效

    keywords: set[str] = field(default_factory=set)
    builtins: set[str] = field(default_factory=set)        # 内建函数（补全候选 + 调用白名单）
    operator_prec: OperatorPrec = field(default_factory=dict)

    # 词法规则由子类提供（按 priority 排序）
    token_rules: list[TokenRule] = field(default_factory=list)

    # 注释起止（用于词法跳过，None 表示不支持）
    line_comment: Optional[str] = None       # 如 "//" 或 "#"
    block_comment_start: Optional[str] = None  # 如 "/*"
    block_comment_end: Optional[str] = None    # 如 "*/"

    def completion_keywords(self) -> list[str]:
        """关键字补全候选（排序后返回）。"""
        return sorted(self.keywords)

    def completion_builtins(self) -> list[str]:
        """内建函数补全候选。"""
        return sorted(self.builtins)
