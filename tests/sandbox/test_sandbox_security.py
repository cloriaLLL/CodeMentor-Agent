"""统一安全检查测试：5 语言 forbidden 命中 + 误报放行。"""
from __future__ import annotations

import pytest

from agents.sandbox_exceptions import SecurityViolationError
from agents.sandbox_security import is_safe, validate_code_safety


@pytest.mark.parametrize("code,lang", [
    ("import os\nos.system('x')", "python"),
    ("import subprocess", "python"),
    ("import shutil", "python"),
    ("import socket", "python"),
    ("os.popen('x')", "python"),
    ("os.execv('x', [])", "python"),
    ("os.spawnl(0, 'x')", "python"),
    ("os.remove('x')", "python"),
    ("os.rmdir('x')", "python"),
    ("os.mkdir('x')", "python"),
    ("os.chdir('x')", "python"),
    ("subprocess.run([])", "python"),
    ("shutil.rmtree('x')", "python"),
    ("eval('1')", "python"),
    ("exec('1')", "python"),
    ("compile('x', 'y', 'exec')", "python"),
    ("__import__('os')", "python"),
    ("open('/etc/passwd')", "python"),
    ("open('../etc/passwd')", "python"),
    ("open('./../etc/passwd')", "python"),   # 问题 B 修复后命中
    ("require('child_process')", "javascript"),
    ('require("fs")', "javascript"),
    ("const cp = child_process", "javascript"),
    ("process.exit(1)", "javascript"),
    ("eval('1')", "javascript"),
    ("new Function('x')", "javascript"),
    ("rm -rf /", "bash"),
    ("rm -rf / ", "bash"),
    ("mkfs.ext4 /dev/sda", "bash"),
    (":(){ :|:& };:", "bash"),
    ("> /dev/sda", "bash"),
    ("dd if=/dev/zero of=/dev/sda", "bash"),
    ("Runtime.getRuntime().exec('x')", "java"),
    ("new ProcessBuilder()", "java"),
    ("java.nio.file.Files.readAllBytes(null)", "java"),
    ("System.Diagnostics.Process.Start('x')", "csharp"),
    ("File.Delete('x')", "csharp"),
    ("Directory.Delete('x')", "csharp"),
])
def test_forbidden_blocked(code, lang):
    with pytest.raises(SecurityViolationError):
        validate_code_safety(code, lang)


@pytest.mark.parametrize("code,lang", [
    ("re.compile('x')", "python"),        # 问题 A：方法调用不误杀
    ("compile_count = 5", "python"),      # 非调用形式
    ("open('data.txt')", "python"),       # 相对路径不误杀
    ('open("out.txt")', "python"),
    ("rm -rf /tmp/x", "bash"),            # 非 root 不误杀
    ("echo hello", "bash"),
    ("console.log('hi')", "javascript"),
    ("const x = 1", "javascript"),
    ("System.out.println('x')", "java"),  # java 仅拦 Process/Files
    ("Console.WriteLine('x')", "csharp"),  # csharp 仅拦 File/Directory/Process
])
def test_false_positives_allowed(code, lang):
    assert is_safe(code, lang) is True


def test_unknown_language_passthrough():
    # 未注册语言不检查（由 get_runtime 在使用时拒绝）
    validate_code_safety("import os", "rust")  # 不抛
    assert is_safe("import os", "rust") is True


def test_alias_uses_python_rules():
    with pytest.raises(SecurityViolationError):
        validate_code_safety("import os", "py")
    with pytest.raises(SecurityViolationError):
        validate_code_safety("eval('1')", "python3")


def test_empty_code_safe():
    assert is_safe("", "python") is True
