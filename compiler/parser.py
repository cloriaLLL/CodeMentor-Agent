"""CodeMentor Agent — 通用语法分析器。

递归下降（语句级）+ Pratt parser（表达式级）混合方案：
- 语句级用递归下降：结构清晰、易教学（let / if / while / func / return / print）
- 表达式级用 Pratt parser：运算符优先级天然处理，避免左递归
- panic mode 错误恢复：遇错同步到下一语句边界（; 或换行）继续，
  保证一次编译产出尽可能多的诊断信息（IDE 友好）

AST 节点见 ast_nodes.py，均为 frozen dataclass，可哈希便于缓存。

依据：DOC-05 §3.2 语法分析器
"""
from __future__ import annotations

from typing import Optional

from compiler.ast_nodes import (
    Program, Block, NumberLit, StringLit, BooleanLit, VarDecl, VarRef,
    Assign, BinaryOp, UnaryOp, Call, FuncDecl, If, While, Return, ExprStmt, Param,
    Node,
)
from compiler.diagnostics import (
    Diagnostic, DiagnosticSeverity, ErrorCode, friendly_message,
)
from compiler.lang.language_spec import LanguageSpec, Token, TokenType


class ParseError(Exception):
    """语法错误（可恢复，记录为 Diagnostic 后继续）。"""
    def __init__(self, message: str, line: int = 0, column: int = 0,
                 error_code: str = ErrorCode.SYN_UNEXPECTED_TOKEN):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.error_code = error_code

    def to_diagnostic(self) -> Diagnostic:
        return Diagnostic(
            line=self.line, column=self.column,
            message=self.message,
            severity=DiagnosticSeverity.ERROR,
            error_code=self.error_code,
        )


# 语句起始关键字（用于 panic mode 同步点判定）
_STMT_KEYWORDS = {"let", "print", "if", "else", "while", "func", "return"}


class Parser:
    """语法分析器。

    用法：
        parser = Parser(spec, tokens)
        ast, diagnostics = parser.parse()
    """

    def __init__(self, spec: LanguageSpec, tokens: list[Token]) -> None:
        self._spec = spec
        self._tokens = tokens
        self._pos = 0
        self.diagnostics: list[Diagnostic] = []

    # ------------------------------------------------------------------ #
    # token 游标辅助
    # ------------------------------------------------------------------ #

    def _peek(self, offset: int = 0) -> Token:
        idx = self._pos + offset
        if idx >= len(self._tokens):
            return self._tokens[-1]   # EOF
        return self._tokens[idx]

    def _advance(self) -> Token:
        tok = self._peek()
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _check(self, ttype: TokenType, value: Optional[str] = None) -> bool:
        tok = self._peek()
        if tok.type != ttype:
            return False
        return value is None or tok.value == value

    def _check_keyword(self, kw: str) -> bool:
        tok = self._peek()
        return tok.type == TokenType.KEYWORD and tok.value == kw

    def _check_punct(self, value: str) -> bool:
        return self._check(TokenType.PUNCT, value)

    def _check_op(self, value: str) -> bool:
        return self._check(TokenType.OP, value)

    def _match(self, ttype: TokenType, value: Optional[str] = None) -> Optional[Token]:
        if self._check(ttype, value):
            return self._advance()
        return None

    def _match_punct(self, value: str) -> Optional[Token]:
        return self._match(TokenType.PUNCT, value)

    def _match_op(self, value: str) -> Optional[Token]:
        return self._match(TokenType.OP, value)

    def _expect(self, ttype: TokenType, value: Optional[str] = None,
                error_code: str = ErrorCode.SYN_EXPECTED_TOKEN) -> Token:
        """期望特定 token，不匹配则抛 ParseError。"""
        if self._check(ttype, value):
            return self._advance()
        tok = self._peek()
        expected = value if value else ttype.value
        raise ParseError(
            friendly_message(
                ErrorCode.SYN_EXPECTED_TOKEN,
                line=tok.line, expected=expected, actual=tok.value or tok.type.value,
            ),
            line=tok.line, column=tok.column,
            error_code=error_code,
        )

    def _expect_op(self, value: str) -> Token:
        return self._expect(TokenType.OP, value)

    def _expect_punct(self, value: str) -> Token:
        return self._expect(TokenType.PUNCT, value)

    # ------------------------------------------------------------------ #
    # 解析入口
    # ------------------------------------------------------------------ #

    def parse(self) -> tuple[Program, list[Diagnostic]]:
        """解析整个程序，返回 (AST, diagnostics)。"""
        statements: list[Node] = []
        # 跳过前导换行
        while not self._at_end():
            try:
                stmt = self._parse_statement()
                if stmt is not None:
                    statements.append(stmt)
            except ParseError as e:
                self.diagnostics.append(e.to_diagnostic())
                self._synchronize()

        ast = Program(statements=tuple(statements))
        return ast, self.diagnostics

    # ------------------------------------------------------------------ #
    # 语句解析（递归下降）
    # ------------------------------------------------------------------ #

    def _parse_statement(self) -> Optional[Node]:
        tok = self._peek()

        # 空语句：;
        if self._match_punct(";"):
            return None

        if tok.type == TokenType.KEYWORD:
            if tok.value == "let":
                return self._parse_let()
            if tok.value == "print":
                return self._parse_print()
            if tok.value == "if":
                return self._parse_if()
            if tok.value == "while":
                return self._parse_while()
            if tok.value == "func":
                return self._parse_func()
            if tok.value == "return":
                return self._parse_return()

        # 赋值或表达式语句
        return self._parse_assignment_or_expr_stmt()

    def _parse_let(self) -> Node:
        kw = self._advance()   # 'let'
        name_tok = self._expect(TokenType.IDENT, error_code=ErrorCode.SYN_EXPECTED_TOKEN)
        self._expect_op("=")
        value = self._parse_expression()
        self._consume_terminator()
        return VarDecl(
            name=name_tok.value, value=value,
            line=kw.line, column=kw.column,
        )

    def _parse_print(self) -> Node:
        kw = self._advance()   # 'print'
        self._expect_punct("(")
        args: list[Node] = []
        if not self._check_punct(")"):
            args.append(self._parse_expression())
            while self._match_punct(","):
                args.append(self._parse_expression())
        self._expect_punct(")")
        self._consume_terminator()
        return ExprStmt(
            expr=Call(
                callee="print", args=tuple(args),
                line=kw.line, column=kw.column,
            ),
            line=kw.line, column=kw.column,
        )

    def _parse_if(self) -> Node:
        kw = self._advance()   # 'if'
        self._expect_punct("(")
        cond = self._parse_expression()
        self._expect_punct(")")
        then_body = self._parse_block_or_stmt()

        else_body = None
        if self._check_keyword("else"):
            self._advance()
            # else if 链
            if self._check_keyword("if"):
                else_body = Block(
                    statements=(self._parse_if(),),
                    line=self._peek().line, column=self._peek().column,
                )
            else:
                else_body = self._parse_block_or_stmt()

        return If(
            condition=cond, then_body=then_body, else_body=else_body,
            line=kw.line, column=kw.column,
        )

    def _parse_while(self) -> Node:
        kw = self._advance()   # 'while'
        self._expect_punct("(")
        cond = self._parse_expression()
        self._expect_punct(")")
        body = self._parse_block_or_stmt()
        return While(
            condition=cond, body=body,
            line=kw.line, column=kw.column,
        )

    def _parse_func(self) -> Node:
        kw = self._advance()   # 'func'
        name_tok = self._expect(TokenType.IDENT)
        self._expect_punct("(")
        params: list[Param] = []
        if not self._check_punct(")"):
            p = self._expect(TokenType.IDENT)
            params.append(Param(name=p.value, line=p.line, column=p.column))
            while self._match_punct(","):
                p = self._expect(TokenType.IDENT)
                params.append(Param(name=p.value, line=p.line, column=p.column))
        self._expect_punct(")")
        body = self._parse_block()
        return FuncDecl(
            name=name_tok.value, params=tuple(params), body=body,
            line=kw.line, column=kw.column,
        )

    def _parse_return(self) -> Node:
        kw = self._advance()   # 'return'
        value = None
        # return 后无表达式（裸 return）或紧跟表达式
        if not (self._check_punct(";") or self._check_punct("}") or self._at_end()
                or self._peek().type == TokenType.NEWLINE):
            value = self._parse_expression()
        self._consume_terminator()
        return Return(value=value, line=kw.line, column=kw.column)

    def _parse_assignment_or_expr_stmt(self) -> Node:
        """解析赋值或表达式语句。

        策略：若当前是 IDENT 且下一个是 '='（非 '=='），则视为赋值。
        否则按表达式语句解析。
        """
        tok = self._peek()
        # 赋值：IDENT = expr
        if tok.type == TokenType.IDENT and self._peek(1).type == TokenType.OP and self._peek(1).value == "=":
            self._advance()   # IDENT
            self._advance()   # '='
            value = self._parse_expression()
            self._consume_terminator()
            return Assign(name=tok.value, value=value, line=tok.line, column=tok.column)

        # 表达式语句
        expr = self._parse_expression()
        self._consume_terminator()
        return ExprStmt(expr=expr, line=tok.line, column=tok.column)

    def _parse_block_or_stmt(self) -> Block:
        """解析 { } 块或单语句（无大括号）。统一返回 Block。"""
        if self._check_punct("{"):
            return self._parse_block()
        # 单语句块
        stmt = self._parse_statement()
        statements: tuple[Node, ...] = (stmt,) if stmt is not None else ()
        return Block(statements=statements, line=self._peek().line, column=self._peek().column)

    def _parse_block(self) -> Block:
        """解析 { stmts } 块。"""
        lbrace = self._expect_punct("{")
        statements: list[Node] = []
        while not self._check_punct("}") and not self._at_end():
            try:
                stmt = self._parse_statement()
                if stmt is not None:
                    statements.append(stmt)
            except ParseError as e:
                self.diagnostics.append(e.to_diagnostic())
                self._synchronize()
        self._expect_punct("}")
        return Block(statements=tuple(statements), line=lbrace.line, column=lbrace.column)

    def _consume_terminator(self) -> None:
        """消费语句终止符（; 或换行或 } 或 EOF），无则记录警告。"""
        if self._match_punct(";"):
            return
        tok = self._peek()
        # 允许换行 / } / EOF 隐式终止
        if tok.type in (TokenType.NEWLINE, TokenType.EOF):
            return
        if tok.type == TokenType.PUNCT and tok.value in ("}",):
            return
        # 否则记录警告（不中断解析）
        self.diagnostics.append(Diagnostic(
            line=tok.line, column=tok.column,
            message=f"第 {tok.line} 行：语句可能缺少 ';' 终止符",
            severity=DiagnosticSeverity.WARNING,
            error_code=ErrorCode.SYN_EXPECTED_TOKEN,
        ))

    # ------------------------------------------------------------------ #
    # 表达式解析（Pratt parser）
    # ------------------------------------------------------------------ #

    def _parse_expression(self, min_prec: int = 0) -> Node:
        """Pratt 表达式解析。

        策略：
        1. 先解析前缀（数字/字符串/标识符/一元运算/括号）
        2. 循环：若当前是运算符且优先级 >= min_prec，解析为二元运算
        """
        left = self._parse_prefix()
        while True:
            op_tok = self._peek()
            op = op_tok.value
            # 仅当当前 token 是 OP 且在优先级表中
            if op_tok.type != TokenType.OP:
                break
            prec = self._spec.operator_prec.get(op)
            if prec is None or prec < min_prec:
                break
            self._advance()   # 消费运算符
            # 右结合用 prec，左结合用 prec + 1
            right = self._parse_expression(prec + 1)
            left = BinaryOp(
                op=op, left=left, right=right,
                line=op_tok.line, column=op_tok.column,
            )
        return left

    def _parse_prefix(self) -> Node:
        """解析前缀表达式（字面量/标识符/一元运算/括号/调用）。"""
        tok = self._peek()

        # 一元运算：- / not
        if tok.type == TokenType.OP and tok.value == "-":
            self._advance()
            operand = self._parse_expression(self._spec.operator_prec.get("-", 5) + 1)
            return UnaryOp(op="-", operand=operand, line=tok.line, column=tok.column)
        if tok.type == TokenType.OP and tok.value == "not":
            self._advance()
            operand = self._parse_expression(self._spec.operator_prec.get("not", 2) + 1)
            return UnaryOp(op="not", operand=operand, line=tok.line, column=tok.column)

        # 数字
        if tok.type == TokenType.NUMBER:
            self._advance()
            val = float(tok.value)
            # 整数优化存储
            if val.is_integer():
                return NumberLit(value=float(int(val)), line=tok.line, column=tok.column)
            return NumberLit(value=val, line=tok.line, column=tok.column)

        # 字符串
        if tok.type == TokenType.STRING:
            self._advance()
            return StringLit(value=self._unescape_string(tok.value), line=tok.line, column=tok.column)

        # 布尔
        if tok.type == TokenType.KEYWORD and tok.value in ("true", "false"):
            self._advance()
            return BooleanLit(value=(tok.value == "true"), line=tok.line, column=tok.column)

        # 标识符 / 函数调用
        if tok.type == TokenType.IDENT:
            self._advance()
            # 函数调用：IDENT ( args )
            if self._check_punct("("):
                self._advance()   # '('
                args: list[Node] = []
                if not self._check_punct(")"):
                    args.append(self._parse_expression())
                    while self._match_punct(","):
                        args.append(self._parse_expression())
                self._expect_punct(")")
                return Call(
                    callee=tok.value, args=tuple(args),
                    line=tok.line, column=tok.column,
                )
            return VarRef(name=tok.value, line=tok.line, column=tok.column)

        # 括号表达式
        if tok.type == TokenType.PUNCT and tok.value == "(":
            self._advance()
            expr = self._parse_expression()
            self._expect_punct(")")
            return expr

        # 无法识别的前缀
        raise ParseError(
            friendly_message(
                ErrorCode.SYN_UNEXPECTED_TOKEN,
                line=tok.line, token=tok.value or tok.type.value,
            ),
            line=tok.line, column=tok.column,
            error_code=ErrorCode.SYN_UNEXPECTED_TOKEN,
        )

    @staticmethod
    def _unescape_string(raw: str) -> str:
        """处理字符串字面量的转义。去除首尾引号，处理 \\n \\t \\\\ \\' \\"。"""
        # 去除首尾引号
        if len(raw) >= 2 and raw[0] in ("'", '"') and raw[-1] == raw[0]:
            inner = raw[1:-1]
        else:
            inner = raw
        # 转义处理
        result: list[str] = []
        i = 0
        while i < len(inner):
            ch = inner[i]
            if ch == "\\" and i + 1 < len(inner):
                nxt = inner[i + 1]
                mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                           "'": "'", '"': '"', "0": "\0"}
                result.append(mapping.get(nxt, "\\" + nxt))
                i += 2
                continue
            result.append(ch)
            i += 1
        return "".join(result)

    # ------------------------------------------------------------------ #
    # panic mode 错误恢复
    # ------------------------------------------------------------------ #

    def _synchronize(self) -> None:
        """panic mode：跳过 token 直到下一个语句边界，恢复解析。

        同步点：
        - 分号 ;
        - 语句起始关键字（let/print/if/while/func/return）
        - 语句块结束 }
        - 换行
        """
        while not self._at_end():
            tok = self._peek()
            if tok.type == TokenType.PUNCT and tok.value == ";":
                self._advance()
                return
            if tok.type == TokenType.PUNCT and tok.value == "}":
                return   # 不消费，由上层 block 处理
            if tok.type == TokenType.KEYWORD and tok.value in _STMT_KEYWORDS:
                return
            if tok.type == TokenType.NEWLINE:
                self._advance()
                return
            self._advance()
