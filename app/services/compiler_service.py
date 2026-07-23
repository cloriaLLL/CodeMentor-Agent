"""CodeMentor Agent — 编译器服务（服务层编排）。

整合编译器内核、安全四层防御、IDE 语言服务，提供统一的服务接口。

职责：
1. 编译源码（含输入验证 + AST 安全校验 + 编译沙箱 + 产物二次校验）
2. 编译并执行（复用现有沙箱 run_code_simple）
3. 委托 IDE 语言服务（补全/诊断/悬停）

依据：DOC-05 §6 集成设计
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from app.core.logger import get_logger

from compiler import compile_source, CompileResult
from compiler.compiler_security import (
    CompilerSecurityError, SecuritySettings, check_ast_safety,
)
from compiler.compile_sandbox import (
    CompileSandboxSettings, CompilerTimeoutError, compile_in_sandbox,
)
from compiler.diagnostics import Diagnostic, DiagnosticSeverity
from compiler.input_validator import (
    InputValidationError, InputValidationSettings, validate_input,
)

from agents.language_service import LanguageService

logger = get_logger(__name__)


@dataclass
class CompilerServiceSettings:
    """编译器服务配置（从 app Settings 同步）。"""
    enabled: bool = True
    max_source_len: int = 50000
    max_ast_depth: int = 64
    compile_timeout: float = 5.0
    cache_size: int = 256


class CompilerService:
    """编译器服务单例。

    集成编译器内核与四层安全防御，对外提供 compile / compile_and_run /
    语言服务能力。被 AppContainer 懒加载。
    """

    def __init__(self, settings: CompilerServiceSettings | None = None) -> None:
        self._settings = settings or self._load_settings()
        # 配置编译缓存容量
        from compiler.compile_cache import set_cache_maxsize
        set_cache_maxsize(self._settings.cache_size)
        # IDE 语言服务
        self._lang_service = LanguageService()
        logger.info(
            "compiler_service_initialized",
            enabled=self._settings.enabled,
            max_source_len=self._settings.max_source_len,
            compile_timeout=self._settings.compile_timeout,
        )

    @staticmethod
    def _load_settings() -> CompilerServiceSettings:
        """从 app Settings 同步配置。"""
        try:
            app_settings = get_settings()
            return CompilerServiceSettings(
                enabled=getattr(app_settings, "compiler_enabled", True),
                max_source_len=getattr(app_settings, "compiler_max_source_len", 50000),
                max_ast_depth=getattr(app_settings, "compiler_max_ast_depth", 64),
                compile_timeout=getattr(app_settings, "compiler_timeout", 5.0),
                cache_size=getattr(app_settings, "compiler_cache_size", 256),
            )
        except Exception:
            return CompilerServiceSettings()

    # ------------------------------------------------------------------ #
    # 编译
    # ------------------------------------------------------------------ #

    def compile(
        self,
        source: str,
        language: str = "minilang",
        target: str = "python",
        run: bool = False,
    ) -> dict:
        """编译源码，可选执行。

        四层安全防御：
        1. 输入验证（长度/深度/字符集）
        2. 编译沙箱内执行编译（超时/递归限制）
        3. AST 白名单安全校验
        4. 编译产物二次正则校验（执行时由 run_code_simple 触发）

        返回字典（供 API 响应），含 target_code / diagnostics / execution_result。
        """
        if not self._settings.enabled:
            return {
                "status": "error",
                "error": "编译器未启用",
                "diagnostics": [],
            }

        # 第一层：输入验证
        input_settings = InputValidationSettings(
            max_source_len=self._settings.max_source_len,
            max_ast_depth=self._settings.max_ast_depth,
        )
        try:
            validate_input(source, input_settings)
        except InputValidationError as e:
            logger.warning("compiler_input_validation_failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "diagnostics": [e.to_diagnostic().to_dict()],
            }

        # 第二层：编译沙箱内执行编译
        sandbox_settings = CompileSandboxSettings(
            timeout_sec=self._settings.compile_timeout,
        )
        try:
            result: CompileResult = compile_in_sandbox(
                lambda: compile_source(source, language=language, target=target,
                                       skip_cache=False, return_ast=True),
                sandbox_settings,
            )
        except CompilerTimeoutError as e:
            logger.warning("compiler_timeout", source_len=len(source))
            return {
                "status": "error",
                "error": str(e),
                "diagnostics": [{
                    "line": 0, "column": 0, "end_column": None,
                    "message": str(e), "severity": "error",
                    "error_code": e.error_code,
                }],
            }
        except Exception as e:
            logger.exception("compiler_failed", error=str(e))
            return {
                "status": "error",
                "error": f"编译失败: {e}",
                "diagnostics": [],
            }

        # 第三层：AST 白名单安全校验（编译成功且无错误时）
        if not result.has_error and result.ast is not None:
            try:
                check_ast_safety(result.ast)
            except CompilerSecurityError as e:
                logger.warning("compiler_security_violation",
                               error=str(e), error_code=e.error_code)
                return {
                    "status": "error",
                    "error": f"安全限制：{e}",
                    "diagnostics": [e.to_diagnostic().to_dict()],
                    "target_code": "",
                }

        # 第四层：编译产物二次校验 + 执行（复用现有沙箱）
        execution_result = None
        if run and not result.has_error and result.target_code:
            execution_result = self._execute_target(result.target_code, language)

        return {
            "status": "success" if not result.has_error else "error",
            "target_code": result.target_code,
            "diagnostics": [d.to_dict() for d in result.diagnostics],
            "from_cache": result.from_cache,
            "elapsed_sec": round(result.elapsed_sec, 4),
            "execution_result": execution_result,
        }

    def _execute_target(self, target_code: str, source_language: str) -> dict:
        """执行编译产物（复用现有沙箱）。

        产物为 Python 源码，通过 run_code_simple 执行，
        自动触发 validate_code_safety 二次校验（第四层防御）。
        """
        try:
            from agents.sandbox import (
                SecurityViolationError, UnsupportedLanguageError,
                ExecutionError, run_code_simple,
            )
            result = run_code_simple(target_code, "python", timeout=10)
            return {
                "status": "success" if result.status == "success" else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "execution_time_sec": round(result.execution_time_sec, 3),
            }
        except SecurityViolationError as e:
            logger.warning("compiler_product_security_violation", error=str(e))
            return {
                "status": "error",
                "error": f"产物安全校验失败：{e}",
                "stdout": "",
                "stderr": str(e),
            }
        except (UnsupportedLanguageError, ExecutionError) as e:
            return {
                "status": "error",
                "error": str(e),
                "stdout": "",
                "stderr": str(e),
            }

    # ------------------------------------------------------------------ #
    # IDE 语言服务（委托）
    # ------------------------------------------------------------------ #

    def complete(self, source: str, cursor_offset: int,
                 language: str = "minilang") -> list[dict]:
        """自动补全。IDE 语言服务为 best-effort，异常时返回空列表而非 500。"""
        try:
            items = self._lang_service.complete(source, cursor_offset, language)
            return [i.to_dict() for i in items]
        except Exception as e:
            logger.warning("complete_failed", error=str(e))
            return []

    def lint(self, source: str, language: str = "minilang") -> list[dict]:
        """诊断。IDE 语言服务为 best-effort，异常时返回空列表而非 500。"""
        try:
            diags = self._lang_service.lint(source, language)
            return [d.to_dict() for d in diags]
        except Exception as e:
            logger.warning("lint_failed", error=str(e))
            return []

    def hover(self, source: str, offset: int,
              language: str = "minilang") -> dict | None:
        """悬停提示。IDE 语言服务为 best-effort，异常时返回 None 而非 500。"""
        try:
            result = self._lang_service.hover(source, offset, language)
            return result.to_dict() if result else None
        except Exception as e:
            logger.warning("hover_failed", error=str(e))
            return None

    def signature_help(self, source: str, offset: int,
                       language: str = "minilang") -> dict | None:
        """签名帮助。IDE 语言服务为 best-effort，异常时返回 None 而非 500。"""
        try:
            result = self._lang_service.signature_help(source, offset, language)
            return result.to_dict() if result else None
        except Exception as e:
            logger.warning("signature_help_failed", error=str(e))
            return None
