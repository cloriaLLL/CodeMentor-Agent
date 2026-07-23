# DOC-02: Sandbox Executor Engine Specification

> **文档定位**：CodeMentor Agent MVP 沙盒隔离执行引擎规范
> **依据**：`Demo设计.md` §1.1 裁剪矩阵 + §2.2 接口 2/3 处理逻辑；`最终成品设计.md` §2.1 沙盒组件职责
> **状态**：Session 0 规范确立
> **约束**：本地 subprocess + pytest 方案，替代分布式 Docker 容器池

---

## 1. 文档概述

本规范定义 `sandbox.py` 模块的隔离执行机制，用于：
- **Validator Agent 预跑**：在推送给用户前，静默校验 Generator 生成的 Solution + Test Cases
- **用户代码判题**：执行用户提交代码 + 题目测试用例，返回通过率与得分

### 1.1 MVP 裁剪方案（匹配 Demo设计.md §1.1）
- ✅ 采用 FastAPI 本地 `subprocess` 调用 `pytest` 运行隔离目录文件
- ❌ 替代复杂的分布式 Docker 容器池

### 1.2 设计原则
1. **隔离性**：每次执行在独立临时目录，互不干扰
2. **可清理**：执行后强制清理临时文件
3. **安全**：禁止网络访问、限制资源、防止路径越权
4. **结构化输出**：返回可解析的执行结果，不暴露原始 Traceback 给前端

---

## 2. 模块接口契约

### 2.1 对外暴露的函数

```python
# sandbox.py

def run_solution_tests(
    solution_code: str,
    test_cases_code: str,
    timeout: int = 10
) -> ExecutionResult:
    """
    Validator 预跑：执行参考答案 + 测试用例
    用于 Generator-Validator Retry Loop 内部校验
    """

def run_user_code(
    user_code: str,
    test_cases_code: str,
    timeout: int = 10
) -> ExecutionResult:
    """
    用户判题：执行用户代码 + 题目测试用例
    用于 /api/submit_code 端点
    """
```

### 2.2 输入参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `solution_code` / `user_code` | `str` | 待执行的 Python 源码 |
| `test_cases_code` | `str` | pytest 测试用例源码（含 `from solution import xxx`） |
| `timeout` | `int` | 执行超时时间（秒），默认 10 秒 |

### 2.3 输出数据结构

```python
from pydantic import BaseModel, Field
from typing import Literal

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
```

**`status` 字段取值规则：**
| status | 条件 |
|--------|------|
| `passed` | `failed_count=0` 且 `error_count=0` 且 `passed_count>0` |
| `failed` | `failed_count>0` |
| `error` | pytest 收集阶段错误（如 import 失败、语法错误） |
| `timeout` | 执行超过 `timeout` 秒 |

---

## 3. 沙盒隔离机制

### 3.1 临时目录创建

使用 `tempfile.mkdtemp()` 创建独立临时目录：

```python
import tempfile
import os
from pathlib import Path

def _create_sandbox_dir() -> Path:
    """创建独立的沙盒工作目录"""
    sandbox_dir = Path(tempfile.mkdtemp(prefix="codementor_sandbox_"))
    return sandbox_dir
```

### 3.2 文件写入策略

每次执行写入两个文件：
```text
sandbox_dir/
├── solution.py      # 参考答案 或 用户代码
└── test_solution.py # 测试用例（pytest 自动发现 test_*.py）
```

**写入规范：**
```python
def _write_files(sandbox_dir: Path, code: str, tests: str) -> None:
    (sandbox_dir / "solution.py").write_text(code, encoding="utf-8")
    (sandbox_dir / "test_solution.py").write_text(tests, encoding="utf-8")
```

**关键约定：**
- 用户/参考代码固定写入 `solution.py`
- 测试用例文件名固定为 `test_solution.py`（pytest 自动发现 `test_*.py`）
- 测试用例中必须使用 `from solution import xxx` 导入被测代码

### 3.3 清理策略

使用 `try/finally` 确保清理，使用 `shutil.rmtree`：

```python
import shutil

def _cleanup_sandbox(sandbox_dir: Path) -> None:
    """强制清理沙盒目录"""
    try:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    except Exception:
        pass  # 清理失败不阻塞主流程
```

**完整执行流程：**
```python
def _execute_in_sandbox(code: str, tests: str, timeout: int) -> ExecutionResult:
    sandbox_dir = _create_sandbox_dir()
    try:
        _write_files(sandbox_dir, code, tests)
        return _run_pytest(sandbox_dir, timeout)
    except Exception as e:
        return ExecutionResult(
            status="error",
            stderr=str(e),
            traceback=str(e)
        )
    finally:
        _cleanup_sandbox(sandbox_dir)
```

---

## 4. pytest 调用规范

### 4.1 subprocess 命令构造

```python
import subprocess
import sys

def _run_pytest(sandbox_dir: Path, timeout: int) -> ExecutionResult:
    cmd = [
        sys.executable, "-m", "pytest",
        str(sandbox_dir / "test_solution.py"),
        "-v",                          # 详细输出
        "--tb=short",                  # 简短 Traceback
        "--no-header",                 # 不显示头部
        "-q",                          # 安静模式
        f"--rootdir={sandbox_dir}",    # 限制根目录
    ]
    
    result = subprocess.run(
        cmd,
        cwd=str(sandbox_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_build_sandbox_env(),      # 受限环境变量
    )
    
    return _parse_pytest_output(result, timeout)
```

### 4.2 受限环境变量（跨平台兼容）

```python
import os, sys, tempfile

def _build_sandbox_env() -> dict:
    """
    构建受限环境变量，禁止网络访问相关配置
    跨平台兼容：Windows / Linux / macOS
    """
    env = {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "HOME": tempfile.gettempdir(),
    }
    
    # 跨平台 PATH 处理
    if sys.platform == "win32":
        # Windows: 保留系统 PATH（含 Python 解释器路径）
        env["PATH"] = os.environ.get("PATH", "")
        env["USERPROFILE"] = tempfile.gettempdir()
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
    else:
        # Linux / macOS: 限制为系统基础路径
        env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    
    # 禁用代理配置（软限制网络访问）
    env["NO_PROXY"] = "*"
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    env.pop("http_proxy", None)
    env.pop("https_proxy", None)
    
    return env
```

**跨平台说明：**
- Windows 开发环境：保留系统 PATH，确保 `python.exe` 可被 `sys.executable` 找到
- Linux 生产环境：限制 PATH 为 `/usr/local/bin:/usr/bin:/bin`，最小化权限
- 通过 `NO_PROXY=*` 软禁用代理访问

### 4.3 超时处理

```python
import subprocess

def _run_pytest(sandbox_dir: Path, timeout: int) -> ExecutionResult:
    try:
        result = subprocess.run(...)
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            status="timeout",
            stderr=f"Execution timed out after {timeout} seconds",
            execution_time_sec=timeout
        )
```

---

## 5. pytest 结果解析逻辑

### 5.1 输出格式示例

pytest 成功输出：
```
test_solution.py::test_rate_limit_allows_within_limit PASSED [ 33%]
test_solution.py::test_rate_limit_blocks_when_exceeded PASSED [ 66%]
test_solution.py::test_rate_limit_resets_after_period PASSED [100%]
========================= 3 passed in 0.02s =========================
```

pytest 失败输出：
```
test_solution.py::test_rate_limit_allows_within_limit PASSED [ 33%]
test_solution.py::test_rate_limit_blocks_when_exceeded FAILED [ 66%]
test_solution.py::test_rate_limit_resets_after_period PASSED [100%]
========================= 1 failed, 2 passed in 0.04s =========================
```

### 5.2 解析正则

```python
import re

def _parse_pytest_output(result: subprocess.CompletedProcess, timeout: int) -> ExecutionResult:
    stdout = result.stdout
    stderr = result.stderr
    
    # 解析摘要行：如 "3 passed in 0.02s" 或 "1 failed, 2 passed in 0.04s"
    summary_match = re.search(
        r"=?\s*(\d+)\s*passed(?:,\s*(\d+)\s*failed)?(?:,\s*(\d+)\s*error)?\s*in\s*([\d.]+)s",
        stdout
    )
    
    # 解析单条测试结果：PASSED / FAILED / ERROR
    passed_count = len(re.findall(r"PASSED", stdout))
    failed_count = len(re.findall(r"FAILED", stdout))
    error_count = len(re.findall(r"ERROR", stdout))
    
    if summary_match:
        passed_count = int(summary_match.group(1))
        failed_count = int(summary_match.group(2) or 0)
        error_count = int(summary_match.group(3) or 0)
        execution_time = float(summary_match.group(4))
        pytest_summary = summary_match.group(0).strip("=").strip()
    else:
        execution_time = 0.0
        pytest_summary = "No summary found"
    
    total = passed_count + failed_count + error_count
    score = int((passed_count / total * 100)) if total > 0 else 0
    
    # 确定状态
    if result.returncode == 0 and failed_count == 0 and error_count == 0:
        status = "passed"
    elif failed_count > 0:
        status = "failed"
    elif error_count > 0:
        status = "error"
    else:
        status = "error"
    
    # 提取 Traceback 摘要（失败时）
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
```

### 5.3 Traceback 提取

```python
def _extract_traceback(stdout: str) -> str | None:
    """提取失败测试的 Traceback 摘要（限前 500 字符）"""
    tb_match = re.search(
        r"_{5,}\s*test_.*?\s*_{5,}(.*?)(?:=+.*passed|FAILED)",
        stdout,
        re.DOTALL
    )
    if tb_match:
        return tb_match.group(1).strip()[:500]
    return None
```

---

## 6. 安全约束

### 6.1 网络访问限制（MVP 软限制）

MVP 阶段采用环境变量软限制：
- 移除 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量
- 设置 `NO_PROXY=*`

**生产环境增强方案（复赛）：**
- 使用 `seccomp` 或 `AppArmor` 强制禁止 `socket` 系统调用
- 切换至 Docker 容器隔离

### 6.2 资源限制（MVP 软限制）

| 资源 | 限制 | 实现方式 |
|------|------|----------|
| 执行时间 | 10 秒 | `subprocess.run(timeout=10)` |
| 输出大小 | 1 MB | 截断 stdout/stderr |
| 临时文件 | 自动清理 | `shutil.rmtree` |

### 6.3 路径越权防护

```python
def _validate_code_safety(code: str) -> None:
    """基础代码安全检查（防 MVP 阶段明显越权）"""
    forbidden_patterns = [
        r"open\s*\([^)]*\.\.",          # 路径穿越
        r"os\.system\s*\(",              # 系统命令
        r"subprocess\.",                 # 子进程调用
        r"__import__\s*\(\s*['\"]os",   # 动态导入 os
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, code):
            raise SecurityViolationError(f"Forbidden pattern detected: {pattern}")
```

**注意：** 此检查为 MVP 防护层，不能替代真正的沙盒隔离。复赛应迁移到 Docker。

---

## 7. 与 main.py 的集成契约

### 7.1 /api/generate_exercise 调用流程（Validator 预跑）

```python
# main.py 内部逻辑（伪代码）
from sandbox import run_solution_tests
from agents.generator import generate_exercise
from agents.validator import validate_exercise

@app.post("/api/generate_exercise")
async def api_generate_exercise(req: GenerateExerciseRequest):
    for attempt in range(3):  # Retry Loop 上限 3 次
        exercise = generate_exercise(req.node_id)
        result = run_solution_tests(
            solution_code=exercise.reference_solution,
            test_cases_code=exercise.test_cases
        )
        if result.status == "passed":
            return GenerateExerciseResponse(
                status="success",
                exercise_id=exercise.exercise_id,
                problem_statement=exercise.problem_statement,
                starter_code=exercise.starter_code,
                validator_status="PASSED_ZERO_BROKEN"
            )
    # 3 次重试失败
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Generator-Validator retry exhausted", "code": 422}
    )
```

### 7.2 /api/submit_code 调用流程（用户判题）

```python
@app.post("/api/submit_code")
async def api_submit_code(req: SubmitCodeRequest):
    exercise = load_exercise_from_seed(req.exercise_id)
    result = run_user_code(
        user_code=req.user_code,
        test_cases_code=exercise.test_cases
    )
    return SubmitCodeResponse(
        status="success",
        passed=(result.status == "passed"),
        score=result.score,
        pytest_output=result.pytest_summary,
        next_state="EcosystemMode" if result.status == "passed" else "PracticeMode"
    )
```

---

## 8. 异常处理

### 8.1 自定义异常

```python
class SandboxError(Exception):
    """沙盒执行基础异常"""

class SecurityViolationError(SandboxError):
    """代码安全检查未通过"""

class TimeoutError(SandboxError):
    """执行超时"""

class ExecutionError(SandboxError):
    """执行异常"""
```

### 8.2 错误响应映射

| 异常类型 | HTTP Code | message |
|----------|-----------|---------|
| `SecurityViolationError` | 400 | "Code contains forbidden patterns" |
| `TimeoutError` | 408 | "Execution timed out" |
| `ExecutionError` | 500 | "Sandbox execution failed" |

---

## 9. 验收清单 (Acceptance Checklist)

- [ ] `sandbox.py` 模块可独立 import 并调用
- [ ] `run_solution_tests()` 正确执行参考答案 + 测试
- [ ] `run_user_code()` 正确执行用户代码 + 测试
- [ ] 临时目录在执行后自动清理（`tempfile.gettempdir()` 下无残留）
- [ ] pytest 输出正确解析（passed/failed/error 计数）
- [ ] 超时场景返回 `status="timeout"`
- [ ] 代码安全检查拦截明显越权（如 `os.system`）
- [ ] `ExecutionResult` 结构符合 Pydantic 模型
- [ ] 失败场景返回结构化 Traceback 摘要（不暴露原始堆栈）

---

## 10. 依赖关系

- **上游依赖**：无（本规范为基础沙盒引擎）
- **下游消费**：
  - DOC-01（后端路由）：`/api/generate_exercise` 和 `/api/submit_code` 调用沙盒
  - DOC-03（Agent 工作流）：Validator Agent 内部调用 `run_solution_tests`
- **测试约定**：
  - 测试用例文件名必须为 `test_solution.py`
  - 测试用例中导入语句必须为 `from solution import xxx`

---

## 11. 测试用例文件约定（重要）

Generator 生成的 `test_cases_code` 必须遵循：

```python
# test_cases_code 模板
import pytest
from solution import rate_limit  # 必须从 solution 模块导入

def test_xxx():
    # 断言逻辑
    ...
```

**禁止行为：**
- ❌ 在测试用例中直接内嵌被测函数定义
- ❌ 使用 `from test_solution import xxx`（自身导入）
- ❌ 使用相对路径 `from .solution import xxx`
