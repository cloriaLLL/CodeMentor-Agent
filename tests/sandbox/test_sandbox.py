"""Sandbox executor engine smoke tests (DOC-02 contracts)."""
from __future__ import annotations

import pytest

from agents.sandbox import (
    ExecutionResult,
    SecurityViolationError,
    run_solution_tests,
    run_user_code,
)

_PASSING_SOLUTION = (
    "def rate_limit(max_calls, period):\n"
    "    def decorator(func):\n"
    "        calls = []\n"
    "        def wrapper(*args, **kwargs):\n"
    "            import time\n"
    "            now = time.time()\n"
    "            calls[:] = [t for t in calls if now - t < period]\n"
    "            if len(calls) >= max_calls:\n"
    "                raise RuntimeError('Rate limit exceeded')\n"
    "            calls.append(now)\n"
    "            return func(*args, **kwargs)\n"
    "        return wrapper\n"
    "    return decorator\n"
)

_TEST_CASES = (
    "import pytest\n"
    "from solution import rate_limit\n\n"
    "def test_allows_within_limit():\n"
    "    @rate_limit(max_calls=3, period=60)\n"
    "    def f():\n"
    "        return 'ok'\n"
    "    assert f() == 'ok'\n"
    "    assert f() == 'ok'\n\n"
    "def test_blocks_when_exceeded():\n"
    "    @rate_limit(max_calls=2, period=60)\n"
    "    def f():\n"
    "        return 'ok'\n"
    "    f()\n"
    "    f()\n"
    "    with pytest.raises(RuntimeError):\n"
    "        f()\n"
)


def test_run_user_code_passes():
    result = run_user_code(_PASSING_SOLUTION, _TEST_CASES, timeout=20)
    assert isinstance(result, ExecutionResult)
    assert result.status == "passed", result.pytest_summary
    assert result.score == 100


def test_run_solution_tests_passes():
    result = run_solution_tests(_PASSING_SOLUTION, _TEST_CASES, timeout=20)
    assert isinstance(result, ExecutionResult)
    assert result.status == "passed"
    assert result.score == 100


def test_security_violation_raised():
    # os.system( is a forbidden pattern -> SecurityViolationError propagates.
    with pytest.raises(SecurityViolationError):
        run_user_code('import os\nos.system("echo hi")', _TEST_CASES, timeout=10)


def test_failing_solution_marks_failed():
    bad = (
        "def rate_limit(max_calls, period):\n"
        "    def decorator(func):\n"
        "        return func\n"
        "    return decorator\n"
    )
    result = run_user_code(bad, _TEST_CASES, timeout=20)
    # A failing solution must be reported as failed with a sub-100 score.
    # The pytest summary parser now handles both "X failed, Y passed" and
    # "Y passed, X failed" orderings (PASSED/FAILED keyword fallback).
    assert result.status == "failed"
    assert result.score < 100
