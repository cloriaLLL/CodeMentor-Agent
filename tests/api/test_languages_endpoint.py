"""GET /api/languages 端点合约测试。"""
from __future__ import annotations


def test_languages_endpoint(client):
    res = client.get("/api/languages")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    names = {lang["language"] for lang in body["languages"]}
    assert {"python", "javascript", "bash", "java", "csharp"} <= names
    py = next(lang for lang in body["languages"] if lang["language"] == "python")
    assert py["installed"] is True
    assert py["supports_tests"] is True
    assert py["is_compiled"] is False
    assert py["file_extension"] == ".py"
    assert py["display_name"] == "Python"


def test_languages_endpoint_compiled_flags(client):
    res = client.get("/api/languages")
    body = res.json()
    by_name = {lang["language"]: lang for lang in body["languages"]}
    assert by_name["java"]["is_compiled"] is True
    assert by_name["csharp"]["is_compiled"] is True
    assert by_name["javascript"]["is_compiled"] is False
    assert by_name["bash"]["is_compiled"] is False


def test_languages_endpoint_field_completeness(client):
    res = client.get("/api/languages")
    body = res.json()
    for lang in body["languages"]:
        assert "docker_image" in lang  # 可为 None，但键必须存在
        assert "display_name" in lang
        assert "file_extension" in lang
        assert "installed" in lang
        assert "supports_tests" in lang
        assert "is_compiled" in lang
