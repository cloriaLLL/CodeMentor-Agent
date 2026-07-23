"""CodeMentor Agent — 编译器内核单元测试。

覆盖：词法分析、语法分析、代码生成、编译缓存、端到端编译。

依据：DOC-05 §10 阶段 B 验收标准
"""
from __future__ import annotations

import pytest

from compiler import compile_source, Diagnostic
from compiler.compile_cache import cache_key, get_cache, CompileCache
from compiler.codegen import PythonCodegen, get_codegen
from compiler.lang import get_spec
from compiler.lang.language_spec import TokenType
from compiler.lexer import Lexer
from compiler.parser import Parser


# --------------------------------------------------------------------------- #
# 词法分析测试
# --------------------------------------------------------------------------- #

class TestLexer:
    def setup_method(self) -> None:
        self.spec = get_spec("minilang")
        self.lexer = Lexer(self.spec)

    def test_number(self) -> None:
        tokens, diags = self.lexer.tokenize("42")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "42"
        assert not diags

    def test_float(self) -> None:
        tokens, _ = self.lexer.tokenize("3.14")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == "3.14"

    def test_string(self) -> None:
        tokens, _ = self.lexer.tokenize('"hello"')
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == '"hello"'

    def test_keyword_priority(self) -> None:
        """关键字应优先于标识符。"""
        tokens, _ = self.lexer.tokenize("let")
        assert tokens[0].type == TokenType.KEYWORD
        assert tokens[0].value == "let"

    def test_ident_not_keyword(self) -> None:
        """lets 不应被识别为 let 关键字。"""
        tokens, _ = self.lexer.tokenize("lets")
        assert tokens[0].type == TokenType.IDENT
        assert tokens[0].value == "lets"

    def test_multichar_op(self) -> None:
        """多字符运算符优先于单字符。"""
        tokens, _ = self.lexer.tokenize("==")
        assert tokens[0].type == TokenType.OP
        assert tokens[0].value == "=="

    def test_comment_skipped(self) -> None:
        tokens, _ = self.lexer.tokenize("# this is a comment\n42")
        # 第一个非跳过 token 应为 42
        nums = [t for t in tokens if t.type == TokenType.NUMBER]
        assert nums[0].value == "42"

    def test_whitespace_skipped(self) -> None:
        tokens, _ = self.lexer.tokenize("  42  ")
        nums = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(nums) == 1

    def test_line_column_tracking(self) -> None:
        tokens, _ = self.lexer.tokenize("let\nx")
        # 第二行 x
        x_tok = [t for t in tokens if t.value == "x"][0]
        assert x_tok.line == 2
        assert x_tok.column == 1

    def test_illegal_char(self) -> None:
        """非法字符应记录诊断但不中断。"""
        tokens, diags = self.lexer.tokenize("42 @ 3")
        assert any(d.severity == "error" for d in diags)
        nums = [t for t in tokens if t.type == TokenType.NUMBER]
        assert len(nums) == 2


# --------------------------------------------------------------------------- #
# 语法分析测试
# --------------------------------------------------------------------------- #

class TestParser:
    def setup_method(self) -> None:
        self.spec = get_spec("minilang")

    def _parse(self, source: str):
        lexer = Lexer(self.spec)
        tokens, _ = lexer.tokenize(source)
        parser = Parser(self.spec, tokens)
        return parser.parse()

    def test_var_decl(self) -> None:
        ast, diags = self._parse("let x = 10")
        assert not diags
        assert len(ast.statements) == 1

    def test_print_stmt(self) -> None:
        ast, diags = self._parse('print("hello")')
        assert not diags
        assert len(ast.statements) == 1

    def test_arithmetic_precedence(self) -> None:
        """乘法应优先于加法。"""
        from compiler.ast_nodes import BinaryOp, NumberLit
        ast, diags = self._parse("1 + 2 * 3")
        assert not diags
        stmt = ast.statements[0]
        # 顶层应为 +，右侧为 *
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "+"
        assert isinstance(stmt.expr.right, BinaryOp)
        assert stmt.expr.right.op == "*"

    def test_paren_grouping(self) -> None:
        from compiler.ast_nodes import BinaryOp
        ast, diags = self._parse("(1 + 2) * 3")
        assert not diags
        stmt = ast.statements[0]
        # 顶层应为 *，左侧为 +
        assert isinstance(stmt.expr, BinaryOp)
        assert stmt.expr.op == "*"
        assert isinstance(stmt.expr.left, BinaryOp)
        assert stmt.expr.left.op == "+"

    def test_func_decl(self) -> None:
        ast, diags = self._parse("func add(a, b) {\nreturn a + b\n}")
        assert not diags
        assert len(ast.statements) == 1

    def test_if_else(self) -> None:
        ast, diags = self._parse("if (x > 0) {\nprint(x)\n} else {\nprint(0)\n}")
        assert not diags
        assert len(ast.statements) == 1

    def test_while(self) -> None:
        ast, diags = self._parse("while (i < 10) {\ni = i + 1\n}")
        assert not diags
        assert len(ast.statements) == 1

    def test_syntax_error_recovery(self) -> None:
        """语法错误应记录诊断但继续解析（panic mode）。"""
        ast, diags = self._parse("let = 10\nlet y = 20")
        assert any(d.severity == "error" for d in diags)
        # 第二条语句应被恢复解析
        assert len(ast.statements) >= 1

    def test_multiple_errors(self) -> None:
        """一次编译应产出多个错误。"""
        ast, diags = self._parse("let = \nlet = \nlet = ")
        errors = [d for d in diags if d.severity == "error"]
        assert len(errors) >= 2


# --------------------------------------------------------------------------- #
# 代码生成测试
# --------------------------------------------------------------------------- #

class TestCodegen:
    def test_simple_codegen(self) -> None:
        result = compile_source("let x = 42")
        assert not result.has_error
        assert "x = 42" in result.target_code

    def test_print_codegen(self) -> None:
        result = compile_source('print("hello")')
        assert not result.has_error
        assert "print(" in result.target_code

    def test_func_codegen(self) -> None:
        result = compile_source("func add(a, b) {\nreturn a + b\n}")
        assert not result.has_error
        assert "def add(a, b):" in result.target_code
        assert "return (a + b)" in result.target_code

    def test_string_escape_safety(self) -> None:
        """字符串内的 Python 代码应被转义，无法逃逸。"""
        # 尝试在字符串中注入 Python 代码
        malicious = 'print("hello\\nimport os")'
        result = compile_source(malicious)
        assert not result.has_error
        # 产物中 import os 必须仍在字符串字面量内（repr 转义）
        # 验证：产物里 'import os' 作为字符串内容，不是独立语句
        lines = result.target_code.split("\n")
        import_lines = [l for l in lines if "import os" in l]
        for l in import_lines:
            # 必须在 print(...) 内，即行内有 print( 且 import os 在引号内
            assert "print(" in l, f"代码注入风险：{l}"

    def test_arithmetic_codegen(self) -> None:
        result = compile_source("let x = 1 + 2 * 3")
        assert not result.has_error
        assert "(1 + (2 * 3))" in result.target_code

    def test_if_codegen(self) -> None:
        result = compile_source("if (x > 0) {\nprint(x)\n}")
        assert not result.has_error
        assert "if (x > 0):" in result.target_code
        assert "print(x)" in result.target_code

    def test_unknown_target(self) -> None:
        with pytest.raises(Exception):
            get_codegen("unknown_target")


# --------------------------------------------------------------------------- #
# 编译缓存测试
# --------------------------------------------------------------------------- #

class TestCompileCache:
    def test_cache_hit(self) -> None:
        """相同源码第二次编译应命中缓存。"""
        get_cache().clear()
        r1 = compile_source("let x = 42")
        assert not r1.from_cache
        r2 = compile_source("let x = 42")
        assert r2.from_cache

    def test_cache_miss_on_change(self) -> None:
        get_cache().clear()
        compile_source("let x = 42")
        r2 = compile_source("let y = 42")
        assert not r2.from_cache

    def test_skip_cache(self) -> None:
        get_cache().clear()
        compile_source("let x = 42")
        r2 = compile_source("let x = 42", skip_cache=True)
        assert not r2.from_cache

    def test_cache_key_stability(self) -> None:
        """相同输入应产生相同 key。"""
        k1 = cache_key("minilang", "let x = 1", "python", "minilang-1.0")
        k2 = cache_key("minilang", "let x = 1", "python", "minilang-1.0")
        assert k1 == k2

    def test_cache_key_spec_version(self) -> None:
        """spec_version 变更应使 key 失效。"""
        k1 = cache_key("minilang", "let x = 1", "python", "minilang-1.0")
        k2 = cache_key("minilang", "let x = 1", "python", "minilang-2.0")
        assert k1 != k2

    def test_lru_eviction(self) -> None:
        cache = CompileCache(maxsize=2)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")   # 应淘汰 a
        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"


# --------------------------------------------------------------------------- #
# 端到端测试
# --------------------------------------------------------------------------- #

class TestEndToEnd:
    def test_full_program(self) -> None:
        """完整 MiniLang 程序应正确编译为可运行 Python。"""
        source = """
let x = 10
let y = x * 2 + 1
func add(a, b) {
    return a + b
}
print(add(x, y))
"""
        result = compile_source(source)
        assert not result.has_error, f"编译错误: {result.diagnostics}"
        assert "def add(a, b):" in result.target_code
        assert "print(add(x, y))" in result.target_code

    def test_compile_result_to_dict(self) -> None:
        result = compile_source("let x = 1")
        d = result.to_dict()
        assert "target_code" in d
        assert "diagnostics" in d
        assert "from_cache" in d
