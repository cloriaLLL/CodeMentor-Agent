"""CodeMentor Agent — MiniLang 教学语言规范。

MiniLang 是为验证编译器工具链而设计的最小教学语言，语法刻意简化：
- 支持变量声明、赋值、算术/比较/逻辑运算
- 支持 if/else、while、func/return
- 内建 print/len/range/abs/min/max 等函数
- 语法示例：
    let x = 10
    let y = x * 2 + 1
    func add(a, b) {
        return a + b
    }
    print(add(x, y))

设计目标：语法最小化，足以演示词法/语法/代码生成全流程，
同时支持 IDE 补全（关键字表 + 内建函数表）。

依据：DOC-05 §3.5 MiniLang 规范
"""
from __future__ import annotations

from compiler.lang.language_spec import LanguageSpec, TokenRule, TokenType


class MiniLangSpec(LanguageSpec):
    """MiniLang 语言规范实例。"""

    def __init__(self) -> None:
        super().__init__(
            language="minilang",
            aliases=("ml", "mini"),
            display_name="MiniLang（教学语言）",
            spec_version="minilang-1.0",
            keywords={
                "let", "print", "if", "else", "while",
                "func", "return", "true", "false", "and", "or", "not",
            },
            builtins={
                "print", "len", "range", "abs", "min", "max",
                "str", "int", "float",
            },
            operator_prec={
                "or": 1,
                "and": 2,
                "==": 3, "!=": 3,
                "<": 4, ">": 4, "<=": 4, ">=": 4,
                "+": 5, "-": 5,
                "*": 6, "/": 6, "%": 6,
            },
            line_comment="#",
            block_comment_start=None,
            block_comment_end=None,
        )
        self.token_rules = self._build_rules()

    def _build_rules(self) -> list[TokenRule]:
        """构建 MiniLang 词法规则（按 priority 降序）。

        关键点：
        - 空白与注释 callback 返回 None 表示跳过（不产生 token）
        - 多字符运算符（==, !=, <=, >=）优先于单字符（=, <, >）
        - 数字优先于标识符（避免 123abc 误判）
        """
        return [
            # 空白与换行（跳过，但记录换行用于语句分隔）
            TokenRule("whitespace", r"[ \t]+", TokenType.ERROR, priority=100,
                     callback=lambda v: None),
            TokenRule("newline", r"\r?\n", TokenType.NEWLINE, priority=99,
                     callback=lambda v: None),   # 换行也跳过，语句分隔由 ; 或换行共同决定

            # 注释
            TokenRule("comment", r"#[^\n]*", TokenType.ERROR, priority=98,
                     callback=lambda v: None),

            # 多字符运算符（必须优先于单字符）
            TokenRule("op_eq", r"==", TokenType.OP, priority=90),
            TokenRule("op_ne", r"!=", TokenType.OP, priority=90),
            TokenRule("op_le", r"<=", TokenType.OP, priority=90),
            TokenRule("op_ge", r">=", TokenType.OP, priority=90),
            TokenRule("op_and", r"and\b", TokenType.OP, priority=89),   # \b 防止匹配 andy
            TokenRule("op_or", r"or\b", TokenType.OP, priority=89),
            TokenRule("op_not", r"not\b", TokenType.OP, priority=89),

            # 数字（含小数，不支持科学计数法以简化）
            TokenRule("number", r"\d+\.\d+|\d+", TokenType.NUMBER, priority=80),

            # 字符串（双引号，支持转义 \" \\ \n \t）
            TokenRule("string", r'"(?:\\.|[^"\\])*"', TokenType.STRING, priority=75),
            # 字符串（单引号）
            TokenRule("string2", r"'(?:\\.|[^'\\])*'", TokenType.STRING, priority=74),

            # 标识符 / 关键字（关键字由 Lexer 后处理提升）
            TokenRule("ident", r"[A-Za-z_][A-Za-z0-9_]*", TokenType.IDENT, priority=50),

            # 单字符运算符
            TokenRule("op_assign", r"=", TokenType.OP, priority=40),
            TokenRule("op_lt", r"<", TokenType.OP, priority=40),
            TokenRule("op_gt", r">", TokenType.OP, priority=40),
            TokenRule("op_plus", r"\+", TokenType.OP, priority=40),
            TokenRule("op_minus", r"-", TokenType.OP, priority=40),
            TokenRule("op_star", r"\*", TokenType.OP, priority=40),
            TokenRule("op_slash", r"/", TokenType.OP, priority=40),
            TokenRule("op_percent", r"%", TokenType.OP, priority=40),

            # 标点
            TokenRule("punct", r"[(){},;:]", TokenType.PUNCT, priority=30),

            # 其余字符视为错误（由 Lexer 记录 ERROR token）
        ]
