"""CodeMentor Agent — 自动补全。

基于语法规则 + 符号表 + 上下文提供补全候选。

三类补全源：
1. 关键字补全：输入 'l' → 'let'
2. 内建函数补全：输入 'p' → 'print('
3. 作用域符号补全：解析当前文件已声明的变量/函数名

实现复用 Lexer tokenize 得到光标前的 token 上下文，确定补全前缀；
再解析整个源码得到作用域符号（已声明的 let / func 名）。

性能预算：< 30ms（千行内）。

依据：DOC-05 §4.2 三类补全源
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from compiler.ast_nodes import Program, VarDecl, FuncDecl, Param
from compiler.lang import get_spec
from compiler.lang.language_spec import LanguageSpec, TokenType
from compiler.lexer import Lexer
from compiler.parser import Parser


class CompletionKind(str, Enum):
    """补全项类型。"""
    KEYWORD = "keyword"
    FUNCTION = "function"
    VARIABLE = "variable"
    SNIPPET = "snippet"
    TEXT = "text"


@dataclass(frozen=True)
class CompletionItem:
    """补全候选项。

    insert_text 支持光标占位符 $1（与主流编辑器一致），由前端处理。
    """
    label: str                    # 显示文本
    kind: CompletionKind
    detail: str = ""               # 类型/签名说明
    insert_text: str = ""          # 插入内容（默认等于 label）
    documentation: str = ""        # 悬停文档

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "kind": self.kind.value,
            "detail": self.detail,
            "insert_text": self.insert_text or self.label,
            "documentation": self.documentation,
        }


def complete(
    source: str,
    cursor_offset: int,
    language: str = "minilang",
    max_items: int = 50,
) -> list[CompletionItem]:
    """提供光标位置的补全候选。

    参数：
        source: 源代码
        cursor_offset: 光标字符偏移（0-based）
        language: 语言名
        max_items: 最大候选数（防爆炸）

    返回排序后的候选列表。
    """
    spec = get_spec(language)

    # 1. 提取光标前缀（当前正在输入的标识符）
    prefix = _extract_prefix(source, cursor_offset)

    # 2. 收集作用域符号（已声明的变量/函数）
    scope_symbols = _collect_scope_symbols(source, spec)

    # 3. 合并三类候选源
    items: list[CompletionItem] = []

    # 关键字
    for kw in spec.completion_keywords():
        items.append(CompletionItem(
            label=kw, kind=CompletionKind.KEYWORD,
            detail="关键字",
            insert_text=kw,
        ))

    # 内建函数（带括号 + 光标定位）
    for builtin in spec.completion_builtins():
        items.append(CompletionItem(
            label=builtin,
            kind=CompletionKind.FUNCTION,
            detail="内建函数",
            insert_text=f"{builtin}($1)",
            documentation=_builtin_doc(builtin),
        ))

    # 作用域符号
    for sym in scope_symbols:
        items.append(CompletionItem(
            label=sym.name,
            kind=CompletionKind.VARIABLE if sym.is_var else CompletionKind.FUNCTION,
            detail=sym.detail,
            insert_text=sym.name,
        ))

    # 4. 按前缀过滤
    if prefix:
        prefix_lower = prefix.lower()
        items = [i for i in items if i.label.lower().startswith(prefix_lower)]

    # 5. 排序：精确匹配 > 前缀匹配 > 字母序
    items.sort(key=lambda i: (
        0 if i.label.lower() == prefix.lower() else 1,
        i.label.lower(),
    ))

    return items[:max_items]


@dataclass
class _ScopeSymbol:
    """作用域符号（已声明的变量或函数）。"""
    name: str
    is_var: bool
    detail: str = ""


def _extract_prefix(source: str, cursor_offset: int) -> str:
    """从光标位置向前提取标识符前缀。

    策略：向前扫描直到非标识符字符（非字母数字下划线）。
    光标偏移超出字符串末尾时自动截断（前端可能传入越界值）。
    """
    if cursor_offset <= 0:
        return ""
    # 截断到字符串边界，防止越界访问
    cursor_offset = min(cursor_offset, len(source))
    start = cursor_offset
    while start > 0:
        ch = source[start - 1]
        if ch.isalnum() or ch == "_":
            start -= 1
        else:
            break
    return source[start:cursor_offset]


def _collect_scope_symbols(source: str, spec: LanguageSpec) -> list[_ScopeSymbol]:
    """解析源码，收集已声明的变量与函数名。

    使用宽松解析（忽略错误），仅提取符号名。
    """
    symbols: list[_ScopeSymbol] = []
    try:
        lexer = Lexer(spec)
        tokens, _ = lexer.tokenize(source)
        parser = Parser(spec, tokens)
        ast, _ = parser.parse()

        for node in _walk(ast):
            if isinstance(node, VarDecl):
                symbols.append(_ScopeSymbol(
                    name=node.name, is_var=True, detail="变量"
                ))
            elif isinstance(node, FuncDecl):
                params = ", ".join(p.name for p in node.params)
                symbols.append(_ScopeSymbol(
                    name=node.name, is_var=False,
                    detail=f"函数({params})",
                ))
    except Exception:
        # 解析失败时返回空符号表（不阻塞补全）
        pass
    return symbols


def _walk(node):
    """扁平遍历 AST 节点（复用 ast_nodes.walk 但简化）。"""
    from compiler.ast_nodes import walk
    return walk(node)


def _builtin_doc(name: str) -> str:
    """内建函数文档。"""
    docs = {
        "print": "print(value) — 打印输出到标准输出",
        "len": "len(x) — 返回序列长度",
        "range": "range(n) — 生成 0 到 n-1 的整数序列",
        "abs": "abs(x) — 返回绝对值",
        "min": "min(a, b, ...) — 返回最小值",
        "max": "max(a, b, ...) — 返回最大值",
        "str": "str(x) — 转为字符串",
        "int": "int(x) — 转为整数",
        "float": "float(x) — 转为浮点数",
        "bool": "bool(x) — 转为布尔",
        "round": "round(x) — 四舍五入",
        "sum": "sum(seq) — 求和",
    }
    return docs.get(name, f"{name}() — 内建函数")
