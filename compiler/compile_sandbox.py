"""CodeMentor Agent — 编译沙箱（安全第三层）。

编译过程本身也需要隔离——防止恶意输入触发编译器内部漏洞：
- 正则灾难性回溯（ReDoS）
- 递归下降解析器栈溢出
- 无限循环（编译器 bug）

对策：
1. 线程执行 + join(timeout) 设置编译超时（独立于执行超时）
2. 限制递归深度（sys.setrecursionlimit 局部，编译后恢复）
3. 编译在子线程执行（编译器崩溃不影响主服务）

依据：DOC-05 §5.3 编译沙箱
"""
from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from typing import Callable, TypeVar

from compiler.diagnostics import CompileError, ErrorCode

T = TypeVar("T")


class CompilerTimeoutError(CompileError):
    """编译超时。"""
    def __init__(self, timeout: float):
        super().__init__(
            f"编译超时（{timeout}s），可能为 ReDoS 或无限循环",
            error_code=ErrorCode.SB_COMPILE_TIMEOUT,
        )


class CompilerRecursionError(CompileError):
    """编译递归深度超限。"""
    def __init__(self) -> None:
        super().__init__(
            "编译递归深度超限，可能为栈溢出攻击",
            error_code=ErrorCode.SB_RECURSION_LIMIT,
        )


@dataclass
class CompileSandboxSettings:
    """编译沙箱配置。"""
    timeout_sec: float = 5.0
    recursion_limit: int = 256


def compile_in_sandbox(
    compile_fn: Callable[[], T],
    settings: CompileSandboxSettings | None = None,
) -> T:
    """在资源限制下执行编译。

    在子线程中执行 compile_fn，应用超时与递归深度限制。
    线程被设为 daemon，超时后主线程不等待其结束（最坏情况线程
    仍会随进程退出而终止）。

    注意：Python 线程无法被强制 kill，超时后只能放弃等待结果。
    这是 GIL 语言的固有限制，实际 ReDoS 攻击应靠输入验证与正则
    原子组预防，此处超时是兜底防御。

    参数：
        compile_fn: 无参闭包，执行实际编译
        settings: 沙箱配置

    返回 compile_fn 的返回值。超时抛 CompilerTimeoutError，
    递归超限抛 CompilerRecursionError，其他异常原样抛出。
    """
    if settings is None:
        settings = CompileSandboxSettings()

    result: dict = {"value": None, "error": None, "done": False}
    old_limit = sys.getrecursionlimit()

    def _target() -> None:
        try:
            # 局部降低递归上限，防止恶意深嵌套打爆栈
            sys.setrecursionlimit(settings.recursion_limit)
            result["value"] = compile_fn()
        except RecursionError:
            result["error"] = CompilerRecursionError()
        except Exception as e:
            result["error"] = e
        finally:
            sys.setrecursionlimit(old_limit)
            result["done"] = True

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=settings.timeout_sec)

    if t.is_alive() or not result["done"]:
        # 线程仍在运行 → 超时
        # 注意：daemon 线程无法强制终止，但它不会阻止进程退出
        raise CompilerTimeoutError(settings.timeout_sec)

    if result["error"] is not None:
        raise result["error"]

    return result["value"]   # type: ignore[return-value]


def with_recursion_limit(limit: int):
    """装饰器：在函数执行期间临时设置递归上限。

    用于那些需要比默认更低/更高递归限制的编译步骤。
    """
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            old = sys.getrecursionlimit()
            try:
                sys.setrecursionlimit(limit)
                return fn(*args, **kwargs)
            finally:
                sys.setrecursionlimit(old)
        return wrapper
    return decorator
