"""CodeMentor Agent - 代码质量评估器（纯函数，无 IO/LLM 依赖）。

从原 ExerciseEvaluator 拆分出的 6 个 _assess_* 方法，全部为基于 AST/正则
的启发式评分，不依赖 self 状态，可独立单测。

评分维度：
- assess_code_quality：代码质量（注释/命名/docstring/错误处理）
- assess_structure：结构质量（函数长度/类组织）
- assess_boundary_handling：边界处理（空值/异常/负值检查）
"""
from __future__ import annotations

import ast
import re
from typing import Any


class CodeQualityAssessor:
    """代码质量评估器（纯函数，无 IO/LLM 依赖）。

    所有方法返回 0-100 整数评分，永不因解析失败抛异常（降级扣分而非崩溃）。
    """

    def assess_code_quality(self, code: str, language: str = "python") -> int:
        """Assess code quality (0-100) based on heuristics.

        python 走 AST 精细评估；其他语言走 _assess_code_quality_generic
        （永不因解析失败扣分，修复调试文档 Bug 4）。
        """
        if language == "python":
            return self._assess_code_quality_python(code)
        return self._assess_code_quality_generic(code, language)

    def _assess_code_quality_python(self, code: str) -> int:
        """Python 代码质量评估（AST 启发式，0-100）。"""
        score = 100
        lines = code.strip().split("\n")
        non_empty = [l for l in lines if l.strip()]

        if not non_empty:
            return 0

        # Check for comments
        comment_lines = [l for l in non_empty if l.strip().startswith("#")]
        comment_ratio = len(comment_lines) / len(non_empty)
        if comment_ratio < 0.05:
            score -= 15
        elif comment_ratio > 0.4:
            score -= 5  # Too many comments

        # Check for meaningful names (not all single letters)
        try:
            tree = ast.parse(code)
            single_letter_names = 0
            total_names = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    total_names += 1
                    if len(node.name) <= 2:
                        single_letter_names += 1
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    total_names += 1
                    if len(node.id) <= 2:
                        single_letter_names += 1
            if total_names > 0 and single_letter_names / total_names > 0.5:
                score -= 15
        except SyntaxError:
            score -= 20

        # Check for docstrings
        has_docstring = False
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)):
                        has_docstring = True
                        break
        except SyntaxError:
            pass
        if not has_docstring:
            score -= 10

        # Check for error handling
        has_try = "try:" in code
        if not has_try and len(non_empty) > 10:
            score -= 5

        return max(0, min(100, score))

    def _assess_code_quality_generic(self, code: str, language: str) -> int:
        """通用代码质量评估（非 python 语言，0-100）。

        不依赖 AST（避免 JS/Java/C# 因解析失败被扣分，修复调试文档 Bug 4）。
        按语言注释前缀、命名长度、嵌套深度近似、错误处理模式评分。
        """
        score = 100
        lines = code.strip().split("\n")
        non_empty = [l for l in lines if l.strip()]
        if not non_empty:
            return 0

        # 注释前缀：python/bash 用 #，js/java/csharp 用 //
        comment_prefix = "//" if language in ("javascript", "java", "csharp") else "#"
        comment_lines = [l for l in non_empty if l.strip().startswith(comment_prefix)]
        comment_ratio = len(comment_lines) / len(non_empty)
        if comment_ratio < 0.05:
            score -= 15
        elif comment_ratio > 0.4:
            score -= 5

        # 命名长度：统计标识符，单字母占比过高扣分
        identifiers = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", code)
        keywords = {"if", "else", "for", "while", "return", "function", "def", "class",
                    "var", "let", "const", "int", "void", "public", "private", "static",
                    "new", "try", "catch", "finally", "throw", "throws", "import",
                    "from", "package", "using", "namespace", "true", "false", "null",
                    "this", "self", "println", "print", "console", "System", "length", "String"}
        meaningful = [w for w in identifiers if w not in keywords and not w[0].isupper()]
        if meaningful:
            single_letter = sum(1 for w in meaningful if len(w) <= 2)
            if single_letter / len(meaningful) > 0.5:
                score -= 15

        # 嵌套深度近似：大括号语言统计 { } 平衡深度
        max_depth = 0
        depth = 0
        for l in non_empty:
            depth += l.count("{") - l.count("}")
            if depth < 0:
                depth = 0
            max_depth = max(max_depth, depth)
        if max_depth > 5:
            score -= 10

        # 错误处理模式
        has_error_handling = any(
            k in code for k in ("try", "catch", "except", "throw", "throws", "raise")
        )
        if not has_error_handling and len(non_empty) > 10:
            score -= 5

        return max(0, min(100, score))

    def assess_structure(self, code: str, language: str = "python") -> int:
        """Assess code structure quality (0-100)."""
        if language != "python":
            return self._assess_structure_generic(code, language)
        score = 100
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return 40

        functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        if not functions and not classes:
            return 30

        # Check function length
        for func in functions:
            func_lines = func.end_lineno - func.lineno if hasattr(func, "end_lineno") else 0
            if func_lines > 50:
                score -= 15
            elif func_lines > 30:
                score -= 8

        # Check if code is well organized (has classes for OOP)
        if len(functions) > 5 and not classes:
            score -= 10

        return max(0, min(100, score))

    def _assess_structure_generic(self, code: str, language: str) -> int:
        """非 python 的结构评估（基于函数密度与行数，不依赖 AST）。"""
        score = 100
        lines = code.strip().split("\n")
        non_empty = [l for l in lines if l.strip()]
        if not non_empty:
            return 0

        # 函数/方法计数（按语言关键字近似）
        if language == "javascript":
            func_count = len(re.findall(r"\bfunction\b|=>", code))
        elif language in ("java", "csharp"):
            func_count = len(re.findall(r"(?:public|private|protected|static)\s+[\w<>\[\]]+\s+\w+\s*\(", code))
        else:
            func_count = len(re.findall(r"\bfunction\b|\bfunc\b", code))

        if func_count == 0:
            score -= 20  # 无函数划分

        # 过长文件扣分
        if len(non_empty) > 100:
            score -= 10

        return max(0, min(100, score))

    def assess_boundary_handling(self, code: str, sandbox_result: Any, language: str = "python") -> int:
        """Assess boundary handling based on test results and code patterns."""
        score = 100

        # If tests failed, reduce score
        if sandbox_result.failed_count > 0:
            score -= 20 * sandbox_result.failed_count

        if language != "python":
            # 通用空值/边界关键字检查
            boundary_keywords = ["null", "undefined", "None", "empty", "length",
                                 "isEmpty", "Length", ".Count", "< 0", "<= 0", "<0"]
            found = sum(1 for k in boundary_keywords if k in code)
            if found == 0 and len(code.split("\n")) > 10:
                score -= 20
            elif found == 1:
                score -= 5
            return max(0, min(100, score))

        # Python: 精细正则边界模式
        boundary_patterns = [
            (r"if\s+not\s+", "空值检查"),
            (r"is\s+None", "None检查"),
            (r"if\s+.*len\(\s*\w+\s*\)\s*==\s*0", "空列表检查"),
            (r"raise\s+", "异常抛出"),
            (r"if\s+.*<\s*0|if\s+.*<=\s*0", "负值检查"),
        ]

        found_patterns = 0
        for pattern, desc in boundary_patterns:
            if re.search(pattern, code):
                found_patterns += 1

        if found_patterns == 0 and len(code.split("\n")) > 10:
            score -= 20
        elif found_patterns == 1:
            score -= 5

        return max(0, min(100, score))
