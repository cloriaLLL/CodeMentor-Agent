"""Smoke tests for the verified Demo API contracts.

Mock LLM is forced via conftest. These tests lock the current response shapes
so later refactors cannot silently break a contract. Covers the unified
exercise pipeline (/api/exercise/*, /api/problems, /api/languages).
"""
from __future__ import annotations

import pytest

VALID_NODE = "python.advanced.decorator"


# --------------------------------------------------------------------------- #
# Core verified contracts
# --------------------------------------------------------------------------- #

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert body["version"]


def test_llm_status(client):
    res = client.get("/api/llm_status")
    assert res.status_code == 200
    body = res.json()
    assert "current_model" in body
    assert "available_zhipu_models" in body
    assert isinstance(body["available_zhipu_models"], dict)
    # Mock mode is forced by conftest.
    assert body["provider"] == "mock"
    assert body["is_mock"] is True


def test_set_model_rejected_in_mock(client):
    # Mock provider cannot switch models -> 400 with the provider-guard message.
    res = client.post("/api/set_model", json={"model": "glm-4-flash"})
    assert res.status_code == 400
    assert "无法切换" in res.json()["message"]


def test_teach(client):
    res = client.post("/api/teach", json={"node_id": VALID_NODE, "action": "start"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["state"] == "TeachMode"
    assert body["markdown_content"]


def test_ecosystem_summary(client):
    res = client.post("/api/ecosystem_summary", json={"node_id": VALID_NODE})
    assert res.status_code == 200
    body = res.json()
    assert body["state"] == "EcosystemMode"
    assert body["stack_summary"]


def test_chat(client):
    res = client.post("/api/chat", json={"message": "你好", "history": []})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("success", "fallback")
    assert body["reply"]


def test_chat_stream(client):
    with client.stream(
        "POST", "/api/chat_stream", json={"message": "你好", "history": []}
    ) as resp:
        assert resp.status_code == 200
        text = b"".join(resp.iter_bytes()).decode("utf-8", errors="replace")
    assert "event: start" in text
    assert "data:" in text


# --------------------------------------------------------------------------- #
# /exercise/run — standalone (does NOT use the broken DI helper)
# --------------------------------------------------------------------------- #

def test_exercise_run_allowed(client):
    res = client.post("/api/exercise/run", json={"code": "print('hi')"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "hi" in body["output"]


def test_exercise_run_blocks_forbidden(client):
    res = client.post("/api/exercise/run", json={"code": "import os"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "error"
    assert "安全" in body["error"]


# --------------------------------------------------------------------------- #
# Phase-1 exercise/problem routes — previously broken by hasattr DI bug,
# now fixed with lazy-loading properties on the container.
# --------------------------------------------------------------------------- #

def test_exercise_types(client):
    res = client.get("/api/exercise/types")
    assert res.status_code == 200
    assert isinstance(res.json()["types"], list)


def test_exercise_generate(client):
    res = client.post(
        "/api/exercise/generate",
        json={"exercise_type": "understanding", "knowledge_point": "Python装饰器"},
    )
    assert res.status_code == 200
    assert res.json()["exercise_id"]


def test_problems_list(client):
    res = client.get("/api/problems")
    assert res.status_code == 200
    assert isinstance(res.json()["problems"], list)


def test_problems_tags(client):
    res = client.get("/api/problems/meta/tags")
    assert res.status_code == 200


# --------------------------------------------------------------------------- #
# 多语言 /exercise/run + /languages（Phase 6 扩充）
# --------------------------------------------------------------------------- #

from agents.sandbox_runtime import get_runtime as _get_runtime  # noqa: E402


def test_exercise_run_unsupported_language(client):
    res = client.post("/api/exercise/run", json={"code": "x", "language": "rust"})
    assert res.status_code == 200
    assert res.json()["status"] == "error"


def test_languages_endpoint(client):
    res = client.get("/api/languages")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    names = {lang["language"] for lang in body["languages"]}
    assert "python" in names and "javascript" in names


@pytest.mark.skipif(
    not _get_runtime("javascript").check_availability().installed,
    reason="node 未安装",
)
def test_exercise_run_javascript(client):
    res = client.post(
        "/api/exercise/run",
        json={"code": "console.log('hi')", "language": "javascript"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "hi" in body["output"]


@pytest.mark.skipif(
    not _get_runtime("bash").check_availability().installed,
    reason="bash 未安装",
)
def test_exercise_run_bash(client):
    res = client.post(
        "/api/exercise/run",
        json={"code": "echo hi", "language": "bash"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert "hi" in body["output"]
