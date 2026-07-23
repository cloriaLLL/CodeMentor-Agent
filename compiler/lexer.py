"""CodeMentor Agent — 通用词法分析器。

规则表驱动 + 合并正则优化：
- 所有 TokenRule 编译为单个 master 正则，一次 match 完成全部规则匹配
- 规则按 priority 降序排列，保证关键字优先于标识符
- 错误恢复：非法字符记录 ERROR token 但继续扫描（支持 IDE 实时诊断）
- 单遍扫描，O(n) 时间复杂度

关键字提升：标识符若命中语言关键字表，由 IDENT 升级为 KEYWORD。
callback 机制：规则可声明后处理函数，返回 None 表示跳过该 token
（用于跳过空白、注释）。

依据：DOC-05 §3.1 词法分析器
"""
from __future__ import annotations

import re
from typing import Optional

from compiler.diagnostics import Diagnostic, DiagnosticSeverity, ErrorCode, friendly_message
from compiler.lang.language_spec import LanguageSpec, Token, TokenRule, TokenType


class Lexer:
    """词法分析器。

    用法：
        spec = get_spec("minilang")
        lexer = Lexer(spec)
        tokens, diagnostics = lexer.tokenize(source)
    """

    def __init__(self, spec: LanguageSpec) -> None:
        self._spec = spec
        self._rules: list[TokenRule] = sorted(spec.token_rules, key=lambda r: -r.priority)
        # 合并正则：每条规则用命名组 g{i}，一次 match 尝试所有规则
        # 注意：命名组索引必须稳定，故用 enumerate 生成
        parts = []
        for i, rule in enumerate(self._rules):
            # 用 (?:...) 非捕获组包裹，外层命名组 g{i}
            parts.append(f"(?P<g{i}>{rule.pattern})")
        self._master = re.compile("|".join(parts))
        self._keywords = spec.keywords

    def tokenize(self, source: str) -> tuple[list[Token], list[Diagnostic]]:
        """词法分析，返回 (tokens, diagnostics)。

        tokens 末尾追加 EOF token。
        diagnostics 记录所有词法错误（如未闭合字符串、非法字符）。
        """
        tokens: list[Token] = []
        diagnostics: list[Diagnostic] = []

        offset = 0
        line = 1
        column = 1
        n = len(source)

        while offset < n:
            m = self._master.match(source, offset)
            if not m:
                # 无规则匹配 → 记录错误字符，跳过 1 字符继续
                ch = source[offset]
                diagnostics.append(Diagnostic(
                    line=line, column=column,
                    message=friendly_message(
                        ErrorCode.LEX_UNEXPECTED_CHAR, line=line, char=ch
                    ),
                    severity=DiagnosticSeverity.ERROR,
                    error_code=ErrorCode.LEX_UNEXPECTED_CHAR,
                ))
                # 推进行列号
                if ch == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1
                offset += 1
                continue

            rule_idx = self._last_group(m)
            if rule_idx is None:
                # 理论上不会发生（master 必有匹配组）
                offset += 1
                continue

            rule = self._rules[rule_idx]
            value = m.group()

            # callback 后处理（跳过空白/注释，或转换类型）
            if rule.callback is not None:
                cb_result = rule.callback(value)
                if cb_result is None:
                    # 跳过此 token，仅推进行列号
                    line, column = self._advance_pos(value, line, column)
                    offset = m.end()
                    continue
                ttype, value = cb_result
            else:
                ttype = rule.token_type

            # 关键字提升：IDENT 命中关键字表 → KEYWORD
            if ttype == TokenType.IDENT and value in self._keywords:
                ttype = TokenType.KEYWORD

            tokens.append(Token(
                type=ttype, value=value, line=line, column=column, offset=offset
            ))

            # 推进行列号
            line, column = self._advance_pos(value, line, column)
            offset = m.end()

        # 字符串未闭合检测：扫描阶段已由正则保证（不匹配则进 ERROR 分支），
        # 此处补充：若末尾是孤立的引号，提示未闭合
        if source and source[-1] in ("'", '"') and (len(tokens) == 0 or tokens[-1].type != TokenType.STRING):
            diagnostics.append(Diagnostic(
                line=line, column=column,
                message=friendly_message(ErrorCode.SYN_UNTERMINATED_STRING, line=line),
                severity=DiagnosticSeverity.ERROR,
                error_code=ErrorCode.SYN_UNTERMINATED_STRING,
            ))

        tokens.append(Token(
            type=TokenType.EOF, value="", line=line, column=column, offset=offset
        ))
        return tokens, diagnostics

    @staticmethod
    def _last_group(m: re.Match) -> Optional[int]:
        """返回最后匹配的命名组索引 g{i}。

        re.Match.lastgroup 返回组名（如 'g3'），解析出索引。
        若所有组均为 None（不应发生），返回 None。
        """
        name = m.lastgroup
        if name is None:
            # 遍历找第一个非空组
            for i in range(len(m.groups())):
                if m.group(i + 1) is not None:
                    return i
            return None
        # name 形如 'g3'
        if name.startswith("g"):
            try:
                return int(name[1:])
            except ValueError:
                return None
        return None

    @staticmethod
    def _advance_pos(value: str, line: int, column: int) -> tuple[int, int]:
        """根据匹配文本推进 (line, column) 位置。"""
        nl_count = value.count("\n")
        if nl_count == 0:
            return line, column + len(value)
        # 有换行：行号增加，列号重置为最后一行剩余长度
        last_nl = value.rfind("\n")
        return line + nl_count, len(value) - last_nl - 1 + 1
