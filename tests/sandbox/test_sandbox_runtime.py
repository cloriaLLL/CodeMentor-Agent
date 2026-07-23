"""多语言运行时注册表 + run_code_simple 跨语言测试。"""
from __future__ import annotations

import pytest

from agents.sandbox import SecurityViolationError, SimpleRunResult, run_code_simple
from agents.sandbox_exceptions import UnsupportedLanguageError
from agents.sandbox_runtime import get_runtime, list_runtimes, resolve_language


def test_alias_resolution():
    assert get_runtime("py").language == "python"
    assert get_runtime("python3").language == "python"
    assert get_runtime("js").language == "javascript"
    assert get_runtime("node").language == "javascript"
    assert resolve_language("sh") == "bash"


def test_unknown_language_raises():
    with pytest.raises(UnsupportedLanguageError):
        get_runtime("rust")
    with pytest.raises(UnsupportedLanguageError):
        get_runtime("")


def test_list_runtimes_contains_five():
    names = {rt.language for rt in list_runtimes()}
    assert {"python", "javascript", "bash", "java", "csharp"} <= names


def test_python_runtime_metadata():
    rt = get_runtime("python")
    assert rt.supports_tests is True
    assert rt.is_compiled is False
    av = rt.check_availability()
    assert av.installed is True
    assert rt.docker_image == "python:3.12-slim"


def test_compiled_runtimes_flagged():
    assert get_runtime("java").is_compiled is True
    assert get_runtime("csharp").is_compiled is True
    assert get_runtime("javascript").is_compiled is False
    assert get_runtime("bash").is_compiled is False


def test_run_code_simple_python():
    r = run_code_simple("print('hello')", "python", timeout=10)
    assert isinstance(r, SimpleRunResult)
    assert r.status == "success"
    assert "hello" in r.stdout
    assert r.exit_code == 0


def test_run_code_simple_python_error_exitcode():
    r = run_code_simple("import sys; sys.exit(3)", "python", timeout=10)
    assert r.status == "error"
    assert r.exit_code == 3


@pytest.mark.skipif(
    not get_runtime("javascript").check_availability().installed,
    reason="node 未安装",
)
def test_run_code_simple_javascript():
    r = run_code_simple("console.log('hi')", "javascript", timeout=10)
    assert r.status == "success"
    assert "hi" in r.stdout


@pytest.mark.skipif(
    not get_runtime("bash").check_availability().installed,
    reason="bash 未安装",
)
def test_run_code_simple_bash():
    r = run_code_simple("echo hi", "bash", timeout=10)
    assert r.status == "success"
    assert "hi" in r.stdout


def test_run_code_simple_security_violation():
    with pytest.raises(SecurityViolationError):
        run_code_simple("import os", "python", timeout=10)


def test_run_code_simple_unsupported_language():
    with pytest.raises(UnsupportedLanguageError):
        run_code_simple("x", "rust", timeout=10)
