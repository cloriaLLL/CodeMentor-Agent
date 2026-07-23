"""CodeMentor Agent — 编译器安全 PoC 与攻击向量测试。

验证四层纵深防御对各类攻击的拦截效果：
1. 输入验证层（input_validator）
2. AST 白名单层（compiler_security）
3. 编译沙箱层（compile_sandbox）
4. 编译产物二次校验层（依赖现有 sandbox_security，由 compiler_service 集成）

攻击向量覆盖：
- 代码注入：__import__ / eval / exec / 动态属性
- 资源耗尽：巨型源码 / 深嵌套 / 长循环
- 字符注入：零宽字符 / 控制字符
- 正则灾难：超长标识符
- 字符串逃逸：尝试从字符串字面量逃逸到代码层

依据：DOC-05 §5.5 代码注入防护矩阵
"""
from __future__ import annotations

import pytest

from compiler import compile_source
from compiler.compiler_security import (
    CompilerSecurityError, SecuritySettings, check_ast_safety,
)
from compiler.compile_sandbox import (
    CompileSandboxSettings, CompilerTimeoutError, compile_in_sandbox,
)
from compiler.diagnostics import DiagnosticSeverity
from compiler.input_validator import (
    InputValidationError, InputValidationSettings, validate_input,
)
from compiler.lang import get_spec
from compiler.lexer import Lexer
from compiler.parser import Parser


def _compile_ast(source: str):
    """辅助：编译源码到 AST（跳过缓存，便于安全校验测试）。"""
    spec = get_spec("minilang")
    lexer = Lexer(spec)
    tokens, _ = lexer.tokenize(source)
    parser = Parser(spec, tokens)
    return parser.parse()[0]


# --------------------------------------------------------------------------- #
# 第一层：输入验证
# --------------------------------------------------------------------------- #

class TestInputValidation:
    """验证输入验证层对资源耗尽与字符注入的拦截。"""

    def test_oversized_source_rejected(self) -> None:
        """巨型源码应被拒绝。"""
        settings = InputValidationSettings(max_source_len=1000)
        big = "let x = 1\n" * 1000   # 远超 1000
        with pytest.raises(InputValidationError):
            validate_input(big, settings)

    def test_deep_nesting_rejected(self) -> None:
        """深嵌套应被拒绝。"""
        settings = InputValidationSettings(max_ast_depth=10)
        deep = "(" * 20 + "1" + ")" * 20
        with pytest.raises(InputValidationError):
            validate_input(deep, settings)

    def test_unbalanced_brackets_rejected(self) -> None:
        """括号不匹配应被拒绝。"""
        with pytest.raises(InputValidationError):
            validate_input("(1 + 2")

    def test_control_char_rejected(self) -> None:
        """控制字符（除 \\n \\t \\r）应被拒绝。"""
        with pytest.raises(InputValidationError):
            validate_input("let x = 1\x00")

    def test_zero_width_char_rejected(self) -> None:
        """零宽字符 U+200B 应被拒绝。"""
        with pytest.raises(InputValidationError):
            validate_input("let x\u200B = 1")

    def test_long_line_rejected(self) -> None:
        """超长单行应被拒绝。"""
        settings = InputValidationSettings(max_line_len=100)
        long_line = "let x = " + "a" * 200
        with pytest.raises(InputValidationError):
            validate_input(long_line, settings)

    def test_normal_source_accepted(self) -> None:
        """正常源码应通过验证（无异常）。"""
        validate_input("let x = 42\nprint(x)\n")


# --------------------------------------------------------------------------- #
# 第二层：AST 白名单
# --------------------------------------------------------------------------- #

class TestASTWhitelist:
    """验证 AST 白名单对代码注入的拦截。"""

    def test_import_os_rejected(self) -> None:
        """调用 __import__('os') 应被拒绝（不在白名单）。"""
        # MiniLang 语法不支持 __import__，但若 AST 中出现也应拦截
        from compiler.ast_nodes import Call
        from compiler.ast_nodes import Program, ExprStmt
        ast = Program(
            statements=(ExprStmt(
                expr=Call(callee="__import__", args=()),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_eval_call_rejected(self) -> None:
        """调用 eval 应被拒绝。"""
        from compiler.ast_nodes import Call, Program, ExprStmt, StringLit
        ast = Program(
            statements=(ExprStmt(
                expr=Call(
                    callee="eval",
                    args=(StringLit(value="import os"),),
                    line=1, column=1,
                ),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_getattr_call_rejected(self) -> None:
        """动态属性访问 getattr 应被拒绝。"""
        from compiler.ast_nodes import Call, Program, ExprStmt, StringLit, VarRef
        ast = Program(
            statements=(ExprStmt(
                expr=Call(
                    callee="getattr",
                    args=(VarRef(name="os", line=1, column=1),
                          StringLit(value="system", line=1, column=1)),
                    line=1, column=1,
                ),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_forbidden_ident_os_rejected(self) -> None:
        """标识符 'os' 应被拒绝。"""
        from compiler.ast_nodes import Program, ExprStmt, VarRef
        ast = Program(
            statements=(ExprStmt(
                expr=VarRef(name="os", line=1, column=1),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_dunder_ident_rejected(self) -> None:
        """dunder 标识符 __builtins__ 应被拒绝。"""
        from compiler.ast_nodes import Program, ExprStmt, VarRef
        ast = Program(
            statements=(ExprStmt(
                expr=VarRef(name="__builtins__", line=1, column=1),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_allowed_print_accepted(self) -> None:
        """白名单函数 print 应通过。"""
        from compiler.ast_nodes import Call, Program, ExprStmt, StringLit
        ast = Program(
            statements=(ExprStmt(
                expr=Call(
                    callee="print",
                    args=(StringLit(value="hello", line=1, column=7),),
                    line=1, column=1,
                ),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        check_ast_safety(ast)   # 不抛异常即通过

    def test_user_function_call_allowed(self) -> None:
        """用户自定义函数的调用应被允许（两段式白名单）。"""
        from compiler.ast_nodes import (
            Call, Program, ExprStmt, NumberLit, FuncDecl, Block, Return,
            BinaryOp, VarRef, Param,
        )
        # func double(n) { return n * 2 }  +  print(double(5))
        ast = Program(
            statements=(
                FuncDecl(
                    name="double",
                    params=(Param(name="n", line=1, column=14),),
                    body=Block(
                        statements=(Return(
                            value=BinaryOp(op="*", left=VarRef(name="n", line=2, column=12),
                                           right=NumberLit(value=2.0, line=2, column=16),
                                           line=2, column=14),
                            line=2, column=5,
                        ),),
                        line=1, column=1,
                    ),
                    line=1, column=1,
                ),
                ExprStmt(
                    expr=Call(
                        callee="double",
                        args=(NumberLit(value=5.0, line=4, column=15),),
                        line=4, column=1,
                    ),
                    line=4, column=1,
                ),
            ),
            line=1, column=1,
        )
        # 用户函数调用应通过（不抛异常）
        check_ast_safety(ast)

    def test_unknown_call_rejected(self) -> None:
        """未声明的未知函数调用应被拒绝（防 __import__ 等危险调用）。"""
        from compiler.ast_nodes import Call, Program, ExprStmt, StringLit
        ast = Program(
            statements=(ExprStmt(
                expr=Call(
                    callee="some_unknown_func",
                    args=(StringLit(value="x", line=1, column=1),),
                    line=1, column=1,
                ),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_too_many_args_rejected(self) -> None:
        """过多参数的函数调用应被拒绝。"""
        from compiler.ast_nodes import Call, Program, ExprStmt, NumberLit
        args = tuple(NumberLit(value=float(i), line=1, column=1) for i in range(64))
        ast = Program(
            statements=(ExprStmt(
                expr=Call(callee="print", args=args, line=1, column=1),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_huge_loop_body_rejected(self) -> None:
        """超大循环体应被拒绝。"""
        from compiler.ast_nodes import While, Block, NumberLit, Program, ExprStmt, VarRef
        # 构造超大循环体
        stmts = tuple(
            ExprStmt(expr=NumberLit(value=1.0, line=2, column=5), line=2, column=5)
            for _ in range(300)
        )
        ast = Program(
            statements=(While(
                condition=VarRef(name="x", line=1, column=7),
                body=Block(statements=stmts, line=1, column=1),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)


# --------------------------------------------------------------------------- #
# 第三层：编译沙箱
# --------------------------------------------------------------------------- #

class TestCompileSandbox:
    """验证编译沙箱对资源耗尽的拦截。"""

    def test_normal_compile_completes(self) -> None:
        """正常编译应在沙箱内完成。"""
        result = compile_in_sandbox(lambda: 1 + 1)
        assert result == 2

    def test_timeout_rejected(self) -> None:
        """超时应触发 CompilerTimeoutError。"""
        import time
        settings = CompileSandboxSettings(timeout_sec=0.1)
        with pytest.raises(CompilerTimeoutError):
            compile_in_sandbox(lambda: time.sleep(1), settings)

    def test_recursion_error_caught(self) -> None:
        """递归超限应被捕获。"""
        def deep_recurse(n: int = 0) -> int:
            return deep_recurse(n + 1)
        # recursion_limit=64，递归会很快超限
        settings = CompileSandboxSettings(recursion_limit=64)
        with pytest.raises(Exception):   # CompilerRecursionError 或 RecursionError
            compile_in_sandbox(lambda: deep_recurse(), settings)


# --------------------------------------------------------------------------- #
# 第四层：编译产物二次校验（通过 compiler_service 集成验证）
# --------------------------------------------------------------------------- #

class TestProductSecurity:
    """验证编译产物的安全性（字符串逃逸防护）。

    重点：即使用户在 MiniLang 字符串中构造 Python 代码片段，
    codegen 的 repr() 转义应保证它无法逃逸出字符串字面量。
    """

    def test_string_cannot_escape(self) -> None:
        """字符串中的 Python 代码无法逃逸。"""
        # 尝试在字符串中注入：闭合引号 + Python 语句
        # MiniLang 字符串："hello"  → codegen: 'hello'
        # 若 codegen 错误地直接拼接，可能产生：hello + "; import os"
        malicious_payloads = [
            'print("hello"); import os',
            'print("hello\\"; import os")',
            'print("\\nimport os")',
        ]
        for payload in malicious_payloads:
            result = compile_source(payload, skip_cache=True)
            # 即使编译成功，产物中不应出现独立的 import os 语句
            if not result.has_error:
                lines = result.target_code.split("\n")
                for line in lines:
                    stripped = line.strip()
                    # 产物中不应有作为独立语句的 import os
                    if stripped.startswith("import ") and "os" in stripped:
                        # 必须在字符串内（被引号包裹）
                        # 即该行应以 print( 或类似调用开头
                        assert "print(" in line or "(" in line, \
                            f"代码注入风险：{line}"

    def test_print_with_import_string(self) -> None:
        """print 字符串内含 'import os' 应安全。"""
        result = compile_source('print("import os")', skip_cache=True)
        assert not result.has_error
        # 产物应为单行 print('import os')，import os 在字符串内
        assert "print('import os')" in result.target_code or 'print("import os")' in result.target_code


# --------------------------------------------------------------------------- #
# 端到端：四层纵深防御
# --------------------------------------------------------------------------- #

class TestDefenseInDepth:
    """端到端验证四层防御的协同工作。"""

    def test_safe_program_compiles_and_runs(self) -> None:
        """安全程序应能完整编译。"""
        source = """
let x = 10
let y = x * 2 + 1
print(y)
"""
        result = compile_source(source, skip_cache=True)
        assert not result.has_error
        assert "print(y)" in result.target_code

    def test_layered_defense_blocks_injection(self) -> None:
        """多层防御协同拦截注入尝试。"""
        # 即使绕过输入验证，AST 白名单也应拦截
        from compiler.ast_nodes import Call, Program, ExprStmt, StringLit
        ast = Program(
            statements=(ExprStmt(
                expr=Call(
                    callee="__import__",
                    args=(StringLit(value="os", line=1, column=12),),
                    line=1, column=1,
                ),
                line=1, column=1,
            ),),
            line=1, column=1,
        )
        # AST 白名单应拦截
        with pytest.raises(CompilerSecurityError):
            check_ast_safety(ast)

    def test_all_layers_no_false_positive(self) -> None:
        """四层防御不应误报正常代码。"""
        normal_programs = [
            "let x = 42",
            "print(\"hello world\")",
            "func f(a, b) {\nreturn a + b\n}",
            "if (x > 0) {\nprint(x)\n}",
            "while (i < 10) {\ni = i + 1\n}",
        ]
        for prog in normal_programs:
            # 输入验证
            validate_input(prog)
            # 编译
            result = compile_source(prog, skip_cache=True)
            assert not result.has_error, f"误报：{prog} → {result.diagnostics}"
            # AST 安全校验
            if result.ast is not None:
                check_ast_safety(result.ast)
