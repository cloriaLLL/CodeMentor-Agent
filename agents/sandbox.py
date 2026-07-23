"""CodeMentor Agent MVP — Sandbox Executor Engine (Session 2).

本模块实现隔离代码执行引擎，用于：
- Validator Agent 预跑：校验 Generator 生成的 Solution + Test Cases
- 用户代码判题：执行用户提交代码 + 题目测试用例

实现依据：DOC-02 Sandbox Executor Engine
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from agents.sandbox_exceptions import (
    ExecutionError,
    SandboxError,
    SandboxTimeoutError,
    SecurityViolationError,
    UnsupportedLanguageError,
)
from agents.sandbox_isolation import (
    ProcessTreeIsolator,
    RawResult,
    RunSpec,
    get_isolator,
)
from agents.sandbox_runtime import get_runtime
from agents.sandbox_security import validate_code_safety

# 向后兼容：异常类曾定义在本模块，现统一到 sandbox_exceptions（破循环依赖）。
# 此处 re-export，保护 practice.py / exercise_evaluator.py 等现有导入。
__all__ = [
    "SandboxError",
    "SecurityViolationError",
    "SandboxTimeoutError",
    "ExecutionError",
    "UnsupportedLanguageError",
    "ExecutionResult",
    "SimpleRunResult",
    "run_solution_tests",
    "run_user_code",
    "run_code_simple",
]


# --------------------------------------------------------------------------- #
# ExecutionResult 数据模型 (DOC-02 §2.3)
# --------------------------------------------------------------------------- #

class ExecutionResult(BaseModel):
    status: Literal["passed", "failed", "error", "timeout"] = Field(
        ..., description="执行状态"
    )
    passed_count: int = Field(0, ge=0, description="通过的测试数")
    failed_count: int = Field(0, ge=0, description="失败的测试数")
    error_count: int = Field(0, ge=0, description="错误的测试数")
    total_count: int = Field(0, ge=0, description="总测试数")
    score: int = Field(0, ge=0, le=100, description="得分 0-100")
    stdout: str = Field("", description="标准输出")
    stderr: str = Field("", description="标准错误")
    pytest_summary: str = Field("", description="pytest 摘要行，如 '3 passed in 0.02s'")
    traceback: str | None = Field(None, description="失败时的 Traceback 摘要")
    execution_time_sec: float = Field(0.0, description="执行耗时（秒）")


class SimpleRunResult(BaseModel):
    """单文件直接运行结果（无测试框架），供 /exercise/run 使用。"""
    status: Literal["success", "error", "timeout"] = Field(..., description="执行状态")
    stdout: str = Field("", description="标准输出")
    stderr: str = Field("", description="标准错误")
    exit_code: int | None = Field(None, description="进程退出码")
    execution_time_sec: float = Field(0.0, description="执行耗时（秒）")


# --------------------------------------------------------------------------- #
# 内部辅助函数
# --------------------------------------------------------------------------- #

def _create_sandbox_dir() -> Path:
    """创建独立的沙盒工作目录 (DOC-02 §3.1)"""
    sandbox_dir = Path(tempfile.mkdtemp(prefix="codementor_sandbox_"))
    return sandbox_dir


def _write_files(sandbox_dir: Path, code: str, tests: str) -> None:
    """写入待执行代码与测试用例 (DOC-02 §3.2)

    自动为 Python 测试文件注入 `from solution import *`，
    避免 LLM 生成的测试用例漏写 import 导致 collection error。
    若测试文件已包含 solution 的 import 则跳过注入。
    """
    (sandbox_dir / "solution.py").write_text(code, encoding="utf-8")
    if "from solution" not in tests and "import solution" not in tests:
        tests = "from solution import *\n\n" + tests
    (sandbox_dir / "test_solution.py").write_text(tests, encoding="utf-8")


def _cleanup_sandbox(sandbox_dir: Path) -> None:
    """强制清理沙盒目录 (DOC-02 §3.3)"""
    try:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    except Exception:
        pass


def _build_sandbox_env() -> dict:
    """构建受限环境变量，跨平台兼容 (DOC-02 §4.2)"""
    env = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "HOME": tempfile.gettempdir(),
    }

    if sys.platform == "win32":
        env["PATH"] = os.environ.get("PATH", "")
        env["USERPROFILE"] = tempfile.gettempdir()
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
    else:
        env["PATH"] = "/usr/local/bin:/usr/bin:/bin"

    env["NO_PROXY"] = "*"

    return env


def _validate_code_safety(code: str) -> None:
    """向后兼容入口：等价于统一安全检查 validate_code_safety(code, "python")。

    统一规则定义在 agents/sandbox_security.py（按语言的正则，修复了 re.compile
    误报、open 路径遍历等问题）。保留此函数以兼容 _execute_in_sandbox 内部调用。
    """
    validate_code_safety(code, "python")


def _extract_traceback(stdout: str) -> str | None:
    """提取失败测试的 Traceback 摘要（限前 500 字符）(DOC-02 §5.3)"""
    tb_match = re.search(
        r"_{5,}\s*test_.*?\s*_{5,}(.*?)(?:=+.*passed|FAILED)",
        stdout,
        re.DOTALL
    )
    if tb_match:
        return tb_match.group(1).strip()[:500]
    return None


def _truncate_output(text: str, max_bytes: int = 1_000_000) -> str:
    """截断输出到指定字节数（DOC-02 §6.2 输出大小限制 1MB）"""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n... [truncated]"


def _parse_pytest_output(result: RawResult | subprocess.CompletedProcess, timeout: int) -> ExecutionResult:
    """解析 pytest 输出并构造 ExecutionResult (DOC-02 §5)

    pytest summary 行的 passed/failed/error 顺序不固定（实际常为
    "X failed, Y passed"），因此这里用顺序无关的提取方式：
    1. 先定位 summary 行，再用 finditer 从中提取各类计数。
    2. 若 summary 行缺失（pytest 崩溃等），回退到 -v 结果行关键字计数。

    result 可为 sandbox_isolation.RawResult 或 subprocess.CompletedProcess，
    两者均含 .returncode/.stdout/.stderr（鸭子类型）。
    """
    stdout = _truncate_output(result.stdout)
    stderr = _truncate_output(result.stderr)

    passed_count = 0
    failed_count = 0
    error_count = 0
    execution_time = 0.0
    pytest_summary = "No summary found"

    # 定位 summary 行：形如 "1 failed, 1 passed in 0.02s"（顺序无关）
    summary_line_match = re.search(
        r"((?:\d+\s*(?:passed|failed|error)s?(?:,\s*)?)+)\s*in\s*([\d.]+)s",
        stdout,
    )
    if summary_line_match:
        summary_text = summary_line_match.group(1)
        execution_time = float(summary_line_match.group(2))
        pytest_summary = f"{summary_text.strip()} in {execution_time}s"
        for m in re.finditer(r"(\d+)\s*(passed|failed|error)", summary_text):
            count = int(m.group(1))
            kind = m.group(2)
            if kind == "passed":
                passed_count = count
            elif kind == "failed":
                failed_count = count
            elif kind == "error":
                error_count = count

    # 回退：summary 行未解析到时，用 -v 结果行关键字计数
    if passed_count == 0 and failed_count == 0 and error_count == 0:
        passed_count = len(re.findall(r"\bPASSED\b", stdout))
        failed_count = len(re.findall(r"\bFAILED\b", stdout))
        error_count = len(re.findall(r"\bERROR\b", stdout))

    total = passed_count + failed_count + error_count
    score = int((passed_count / total * 100)) if total > 0 else 0

    if result.returncode == 0 and failed_count == 0 and error_count == 0 and passed_count > 0:
        status = "passed"
    elif failed_count > 0:
        status = "failed"
    elif error_count > 0:
        status = "error"
    else:
        status = "error"

    traceback_summary = _extract_traceback(stdout) if status != "passed" else None

    return ExecutionResult(
        status=status,
        passed_count=passed_count,
        failed_count=failed_count,
        error_count=error_count,
        total_count=total,
        score=score,
        stdout=stdout,
        stderr=stderr,
        pytest_summary=pytest_summary,
        traceback=traceback_summary,
        execution_time_sec=execution_time,
    )


def _run_pytest(sandbox_dir: Path, timeout: int) -> ExecutionResult:
    """在沙盒目录中运行 pytest (DOC-02 §4)

    使用 ProcessTreeIsolator 执行（pytest 显式走本地进程树，不经 Docker），
    超时时杀整个进程组，强化清理。
    """
    cmd = [
        sys.executable, "-m", "pytest",
        str(sandbox_dir / "test_solution.py"),
        "-v",
        "--tb=short",
        "--no-header",
        "-q",
        f"--rootdir={sandbox_dir}",
    ]
    spec = RunSpec(
        cmd=cmd,
        cwd=sandbox_dir,
        timeout=timeout,
        env=_build_sandbox_env(),
        language="python",
        docker_image=None,
    )
    raw = ProcessTreeIsolator().run(spec, sandbox_dir / "test_solution.py")
    if raw.timed_out:
        return ExecutionResult(
            status="timeout",
            stderr=f"Execution timed out after {timeout} seconds",
            execution_time_sec=raw.elapsed,
        )
    return _parse_pytest_output(raw, timeout)


def _execute_in_sandbox(
    code: str, tests: str, timeout: int, language: str = "python"
) -> ExecutionResult:
    """完整沙盒执行流程 (DOC-02 §3.3)

    - python：写 solution.py + test_solution.py，跑 pytest。
    - 非 python：该语言运行时不支持测试框架时，降级为退出码判定
      （见 _execute_non_python），pytest_summary 标注降级模式。

    SecurityViolationError 不在此捕获，向上传播由调用方处理（DOC-02 §8.2）。
    """
    sandbox_dir = _create_sandbox_dir()
    try:
        validate_code_safety(code, language)
        if language == "python":
            _write_files(sandbox_dir, code, tests)
            return _run_pytest(sandbox_dir, timeout)
        return _execute_non_python(sandbox_dir, code, tests, timeout, language)
    except SecurityViolationError:
        raise  # 向上传播，由调用方映射到 HTTP 400
    except Exception as e:
        return ExecutionResult(
            status="error",
            stderr=str(e),
            traceback=str(e)
        )
    finally:
        _cleanup_sandbox(sandbox_dir)


def _execute_non_python(
    sandbox_dir: Path, code: str, tests: str, timeout: int, language: str
) -> ExecutionResult:
    """非 python 语言的降级评判：直接运行用户代码，按退出码判定。

    该语言运行时不接测试框架（supports_tests=False），无法对 test_cases
    做自动断言，故退化为「能跑通即通过」的退出码模式：
    - exit 0 → status=passed, score=100, total_count=1
    - exit !=0 → status=failed, score=0, total_count=1
    - 超时 → status=timeout
    pytest_summary 显式标注 (language=X, exit-code mode)，feedback 由调用方
    据此向用户说明判定方式。
    """
    runtime = get_runtime(language)
    avail = runtime.check_availability()
    if not avail.installed and not runtime.docker_image:
        raise ExecutionError(f"{runtime.display_name} 运行时未安装，无法执行")

    code_file = sandbox_dir / f"snippet{runtime.file_extension}"
    code_file.write_text(code, encoding="utf-8")

    # 编译型语言在此编译；失败抛 CalledProcessError 由上层捕获转 error
    runtime.prepare(code_file, sandbox_dir)

    cmd = runtime.build_run_command(code_file, sandbox_dir)
    env = _build_sandbox_env()
    env.update(runtime.sandbox_env_extras())
    # 编译型或本地未安装时优先 Docker；脚本类本地已装走进程树（更快）
    prefer_docker = runtime.is_compiled or not avail.installed
    isolator = get_isolator(prefer_docker=prefer_docker)
    spec = RunSpec(
        cmd=cmd,
        cwd=sandbox_dir,
        timeout=timeout,
        env=env,
        language=language,
        docker_image=runtime.docker_image,
    )
    raw = isolator.run(spec, code_file)

    summary = f"(language={language}, exit-code mode)"

    if raw.timed_out:
        return ExecutionResult(
            status="timeout",
            stderr=raw.stderr or f"Execution timed out after {timeout} seconds",
            pytest_summary=summary,
            execution_time_sec=raw.elapsed,
        )

    stdout = _truncate_output(raw.stdout)
    stderr = _truncate_output(raw.stderr)
    if raw.returncode == 0:
        return ExecutionResult(
            status="passed",
            passed_count=1,
            total_count=1,
            score=100,
            stdout=stdout,
            stderr=stderr,
            pytest_summary=summary,
            execution_time_sec=raw.elapsed,
        )
    return ExecutionResult(
        status="failed",
        failed_count=1,
        total_count=1,
        score=0,
        stdout=stdout,
        stderr=stderr,
        pytest_summary=summary,
        traceback=stderr[:500] or None,
        execution_time_sec=raw.elapsed,
    )


# --------------------------------------------------------------------------- #
# 对外接口 (DOC-02 §2)
# --------------------------------------------------------------------------- #

def run_solution_tests(
    solution_code: str,
    test_cases_code: str,
    timeout: int = 10,
    language: str = "python",
) -> ExecutionResult:
    """Validator 预跑：执行参考答案 + 测试用例 (DOC-02 §2.1)

    language 默认 python（向后兼容 validator.py / practice.py 现有调用）。
    """
    return _execute_in_sandbox(solution_code, test_cases_code, timeout, language)


def run_user_code(
    user_code: str,
    test_cases_code: str,
    timeout: int = 10,
    language: str = "python",
) -> ExecutionResult:
    """用户判题：执行用户代码 + 题目测试用例 (DOC-02 §2.1)

    language 默认 python（向后兼容 exercise_evaluator.py / practice.py 现有调用）。
    """
    return _execute_in_sandbox(user_code, test_cases_code, timeout, language)


def run_code_simple(
    code: str, language: str = "python", timeout: int = 10
) -> SimpleRunResult:
    """单文件直接运行（无测试框架），供 /exercise/run 使用。

    流程：统一安全检查 → get_runtime + 可用性检测 → 建临时目录写文件 →
    runtime.prepare()（编译型编译）→ get_isolator().run() → 状态映射 → 清理。

    隔离策略：脚本类本地已装走进程树（快）；编译型或本地未装时优先 Docker。
    """
    validate_code_safety(code, language)
    runtime = get_runtime(language)
    avail = runtime.check_availability()
    if not avail.installed and not runtime.docker_image:
        raise ExecutionError(f"{runtime.display_name} 运行时未安装，无法执行")

    sandbox_dir = _create_sandbox_dir()
    try:
        code_file = sandbox_dir / f"snippet{runtime.file_extension}"
        code_file.write_text(code, encoding="utf-8")
        runtime.prepare(code_file, sandbox_dir)

        cmd = runtime.build_run_command(code_file, sandbox_dir)
        env = _build_sandbox_env()
        env.update(runtime.sandbox_env_extras())
        prefer_docker = runtime.is_compiled or not avail.installed
        isolator = get_isolator(prefer_docker=prefer_docker)
        spec = RunSpec(
            cmd=cmd,
            cwd=sandbox_dir,
            timeout=timeout,
            env=env,
            language=language,
            docker_image=runtime.docker_image,
        )
        raw = isolator.run(spec, code_file)

        if raw.timed_out:
            return SimpleRunResult(
                status="timeout",
                stderr=raw.stderr or f"Execution timed out after {timeout} seconds",
                execution_time_sec=raw.elapsed,
            )
        status = "success" if raw.returncode == 0 else "error"
        return SimpleRunResult(
            status=status,
            stdout=raw.stdout,
            stderr=raw.stderr,
            exit_code=raw.returncode,
            execution_time_sec=raw.elapsed,
        )
    finally:
        _cleanup_sandbox(sandbox_dir)
