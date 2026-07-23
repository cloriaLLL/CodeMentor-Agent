"""CodeMentor Agent — 悬停提示与签名帮助。

悬停提示：识别光标下的符号，返回文档字符串。
签名帮助：识别光标所在函数调用的参数位置，返回参数列表。

二者均复用编译器前端的 token 与 AST 分析能力。

依据：DOC-05 §4.1.3 悬停提示与签名帮助
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from compiler.ast_nodes import Call
from compiler.lang import get_spec
from compiler.lang.language_spec import TokenType
from compiler.lexer import Lexer
from compiler.parser import Parser


@dataclass(frozen=True)
class HoverResult:
    """悬停提示结果。"""
    content: str
    range_start: int = 0
    range_end: int = 0

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "range_start": self.range_start,
            "range_end": self.range_end,
        }


@dataclass(frozen=True)
class ParameterInfo:
    """单个参数信息。"""
    label: str
    documentation: str = ""

    def to_dict(self) -> dict:
        return {"label": self.label, "documentation": self.documentation}


@dataclass(frozen=True)
class SignatureInfo:
    """函数签名信息。"""
    label: str                      # 如 "print(value)"
    parameters: tuple[ParameterInfo, ...] = field(default_factory=tuple)
    documentation: str = ""
    active_parameter: int = 0      # 当前光标所在参数索引

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "parameters": [p.to_dict() for p in self.parameters],
            "documentation": self.documentation,
            "active_parameter": self.active_parameter,
        }


@dataclass(frozen=True)
class SignatureHelp:
    """签名帮助结果。"""
    signatures: tuple[SignatureInfo, ...] = field(default_factory=tuple)
    active_signature: int = 0

    def to_dict(self) -> dict:
        return {
            "signatures": [s.to_dict() for s in self.signatures],
            "active_signature": self.active_signature,
        }


# 内建函数签名表
_BUILTIN_SIGNATURES: dict[str, SignatureInfo] = {
    "print": SignatureInfo(
        label="print(value)",
        parameters=(ParameterInfo("value", "要打印的值"),),
        documentation="打印输出到标准输出",
    ),
    "len": SignatureInfo(
        label="len(x)",
        parameters=(ParameterInfo("x", "序列或字符串"),),
        documentation="返回序列长度",
    ),
    "range": SignatureInfo(
        label="range(n)",
        parameters=(ParameterInfo("n", "上限（不包含）"),),
        documentation="生成 0 到 n-1 的整数序列",
    ),
    "abs": SignatureInfo(
        label="abs(x)",
        parameters=(ParameterInfo("x", "数字"),),
        documentation="返回绝对值",
    ),
    "min": SignatureInfo(
        label="min(a, b, ...)",
        parameters=(ParameterInfo("a", "值1"), ParameterInfo("b", "值2")),
        documentation="返回最小值",
    ),
    "max": SignatureInfo(
        label="max(a, b, ...)",
        parameters=(ParameterInfo("a", "值1"), ParameterInfo("b", "值2")),
        documentation="返回最大值",
    ),
    "str": SignatureInfo(
        label="str(x)",
        parameters=(ParameterInfo("x", "要转换的值"),),
        documentation="转为字符串",
    ),
    "int": SignatureInfo(
        label="int(x)",
        parameters=(ParameterInfo("x", "要转换的值"),),
        documentation="转为整数",
    ),
    "float": SignatureInfo(
        label="float(x)",
        parameters=(ParameterInfo("x", "要转换的值"),),
        documentation="转为浮点数",
    ),
}


def hover(
    source: str,
    offset: int,
    language: str = "minilang",
) -> Optional[HoverResult]:
    """获取光标位置的悬停提示。

    策略：
    1. 找到光标所在 token
    2. 若是关键字 → 返回关键字说明
    3. 若是内建函数 → 返回签名
    4. 若是用户符号 → 返回声明信息（如有）
    """
    spec = get_spec(language)
    lexer = Lexer(spec)
    tokens, _ = lexer.tokenize(source)

    # 找到包含光标的 token
    target_token = None
    for tok in tokens:
        if tok.offset <= offset < tok.offset + len(tok.value):
            target_token = tok
            break

    if target_token is None:
        return None

    # 关键字
    if target_token.type == TokenType.KEYWORD:
        return HoverResult(
            content=f"{target_token.value} — 关键字",
            range_start=target_token.offset,
            range_end=target_token.offset + len(target_token.value),
        )

    # 标识符（可能是内建函数或用户符号）
    if target_token.type == TokenType.IDENT:
        name = target_token.value
        # 内建函数
        if name in spec.builtins:
            sig = _BUILTIN_SIGNATURES.get(name)
            doc = sig.documentation if sig else f"{name}() — 内建函数"
            return HoverResult(
                content=f"```\n{sig.label if sig else name + '()'}\n```\n\n{doc}",
                range_start=target_token.offset,
                range_end=target_token.offset + len(name),
            )
        # 用户符号（查找声明）
        try:
            parser = Parser(spec, tokens)
            ast, _ = parser.parse()
            from compiler.ast_nodes import walk, VarDecl, FuncDecl
            for node in walk(ast):
                if isinstance(node, VarDecl) and node.name == name:
                    return HoverResult(
                        content=f"`{name}` — 变量",
                        range_start=target_token.offset,
                        range_end=target_token.offset + len(name),
                    )
                if isinstance(node, FuncDecl) and node.name == name:
                    params = ", ".join(p.name for p in node.params)
                    return HoverResult(
                        content=f"```\nfunc {name}({params})\n```\n\n用户定义函数",
                        range_start=target_token.offset,
                        range_end=target_token.offset + len(name),
                    )
        except Exception:
            pass
        return HoverResult(
            content=f"`{name}` — 标识符",
            range_start=target_token.offset,
            range_end=target_token.offset + len(name),
        )

    return None


def signature_help(
    source: str,
    offset: int,
    language: str = "minilang",
) -> Optional[SignatureHelp]:
    """获取光标所在函数调用的签名帮助。

    策略：
    1. 从光标向前查找最近的未闭合 '('（即包含光标的最内层调用）
    2. 找到 '(' 前的函数名
    3. 计算当前参数索引：从 '(' 到光标，统计深度为 1 的逗号数
    4. 返回签名信息
    """
    spec = get_spec(language)
    lexer = Lexer(spec)
    tokens, _ = lexer.tokenize(source)

    # 先找到光标位置在 token 列表中的索引
    cursor_idx = 0
    for i, tok in enumerate(tokens):
        if tok.offset <= offset:
            cursor_idx = i
        else:
            break

    # 从光标向前查找最近的未闭合 '('（包含光标的最内层调用）
    call_callee: Optional[str] = None
    call_open_idx: Optional[int] = None
    depth = 0
    for i in range(cursor_idx, -1, -1):
        tok = tokens[i]
        if tok.type == TokenType.PUNCT and tok.value == ")":
            depth += 1
        elif tok.type == TokenType.PUNCT and tok.value == "(":
            if depth == 0:
                # 找到包含光标的最内层 '('
                call_open_idx = i
                # 前一个 token 应是函数名
                if i > 0 and tokens[i - 1].type == TokenType.IDENT:
                    call_callee = tokens[i - 1].value
                break
            depth -= 1

    if call_callee is None or call_open_idx is None:
        return None

    # 计算当前参数索引：从 '(' 到光标，统计深度为 1 的顶层逗号数
    # （只计当前调用层级内的逗号，忽略嵌套调用的逗号）
    active_param = 0
    paren_depth = 0
    for i in range(call_open_idx + 1, cursor_idx + 1):
        tok = tokens[i]
        if tok.offset >= offset:
            break
        if tok.type == TokenType.PUNCT and tok.value == "(":
            paren_depth += 1
        elif tok.type == TokenType.PUNCT and tok.value == ")":
            paren_depth -= 1
        elif tok.type == TokenType.PUNCT and tok.value == "," and paren_depth == 0:
            # 顶层逗号（当前调用层级的参数分隔符）
            active_param += 1

    # 查找签名
    sig = _BUILTIN_SIGNATURES.get(call_callee)
    if sig is None:
        # 用户定义函数：从 AST 提取参数
        try:
            parser = Parser(spec, tokens)
            ast, _ = parser.parse()
            from compiler.ast_nodes import walk, FuncDecl
            params_info: list[ParameterInfo] = []
            for node in walk(ast):
                if isinstance(node, FuncDecl) and node.name == call_callee:
                    params_info = [
                        ParameterInfo(p.name, "") for p in node.params
                    ]
                    label = f"func {call_callee}({', '.join(p.label for p in params_info)})"
                    sig = SignatureInfo(
                        label=label,
                        parameters=tuple(params_info),
                        documentation="用户定义函数",
                        active_parameter=min(active_param, max(len(params_info) - 1, 0)) if params_info else 0,
                    )
                    break
        except Exception:
            pass

    if sig is None:
        return None

    return SignatureHelp(signatures=(sig,), active_signature=0)
