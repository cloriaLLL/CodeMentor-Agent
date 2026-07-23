r"""CodeMentor Agent — 统一代码安全检查。

合并原 sandbox.py（正则）与 app/api/exercise.py（字符串匹配）两套规则，
按语言定义 forbidden patterns（正则版本，更精确，避免误报）。

提供统一接口 validate_code_safety(code, language)，供 sandbox.py 与
/exercise/run 端点共同调用，消除规则不一致。

修复的误报 bug：
- compile(  → (?<![\w.])\bcompile\s*\(  不再误杀 re.compile(（与 eval/exec 一致，排除 . 前缀）
- open('/   → open\s*\(\s*['"](?:/|\.\.)  防绝对路径与 .. 开头穿越
- open(.. 跳转) → open\s*\(\s*['"][^'"]*\.\.  封堵 ./../ 、a/../b 等任意位置 .. 跳转
- rm -rf /  → rm\s+-rf\s+/\s*$  精确匹配根目录，不误杀 rm -rf /home/x
"""
from __future__ import annotations

import re

from agents.sandbox_exceptions import SecurityViolationError

# 按语言定义禁止模式：(正则, 人类可读描述)
_FORBIDDEN_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "python": [
        (r"\bimport\s+os\b", "import os"),
        (r"\bimport\s+subprocess\b", "import subprocess"),
        (r"\bimport\s+shutil\b", "import shutil"),
        (r"\bimport\s+socket\b", "import socket"),
        (r"os\.system\s*\(", "os.system"),
        (r"os\.popen\s*\(", "os.popen"),
        (r"os\.exec\w*\s*\(", "os.exec*"),
        (r"os\.spawn\w*\s*\(", "os.spawn*"),
        (r"os\.(?:remove|rmdir|mkdir|chdir)\b", "os 文件系统操作"),
        (r"subprocess\.", "subprocess"),
        (r"shutil\.rmtree", "shutil.rmtree"),
        (r"open\s*\(\s*['\"](?:/|\.\.)", "open 路径遍历"),
        (r"open\s*\(\s*['\"][^'\"]*\.\.", "open 路径遍历（含 .. 跳转）"),
        (r"__import__\s*\(\s*['\"]os", "__import__ os"),
        (r"(?<![\w.])\beval\s*\(", "eval"),
        (r"(?<![\w.])\bexec\s*\(", "exec"),
        (r"(?<![\w.])\bcompile\s*\(", "compile"),
    ],
    "javascript": [
        (r"require\s*\(\s*['\"]child_process['\"]\s*\)", "require child_process"),
        (r"require\s*\(\s*['\"]fs['\"]\s*\)", "require fs"),
        (r"\bchild_process\b", "child_process"),
        (r"process\.exit\b", "process.exit"),
        (r"\beval\s*\(", "eval"),
        (r"new\s+Function\s*\(", "new Function"),
    ],
    "bash": [
        (r"rm\s+-rf\s+/\s*$", "rm -rf /"),
        (r"rm\s+-rf\s+/\s+", "rm -rf 根目录"),
        (r"\bmkfs\b", "mkfs"),
        (r":\(\)\s*\{", "fork bomb"),
        (r">\s*/dev/(?:sda|nvme|hd)", "写入裸设备"),
        (r"\bdd\s+.*of=/dev/", "dd 写入裸设备"),
    ],
    "java": [
        (r"Runtime\.getRuntime\s*\(\s*\)\.exec", "Runtime.exec"),
        (r"\bProcessBuilder\b", "ProcessBuilder"),
        (r"java\.nio\.file\.(?:Files|Paths)\b", "java.nio 文件操作"),
    ],
    "csharp": [
        (r"System\.Diagnostics\.Process", "Process"),
        (r"\bFile\.(?:Delete|Move|WriteAll)\w*\s*\(", "File IO"),
        (r"\bDirectory\.(?:Delete|Move)\s*\(", "Directory IO"),
    ],
}


def validate_code_safety(code: str, language: str = "python") -> None:
    """统一安全检查：违反则抛 SecurityViolationError。

    未知语言不在此处检查（由 sandbox_runtime.get_runtime 在使用时拒绝），
    避免安全模块与运行时注册表强耦合。
    """
    if not code:
        return
    # 延迟导入避免循环依赖
    from agents.sandbox_runtime import get_runtime, resolve_language

    canonical = resolve_language(language)
    # 仅当该语言已注册时才检查
    try:
        get_runtime(language)
    except Exception:
        return

    for pattern, desc in _FORBIDDEN_PATTERNS.get(canonical, []):
        if re.search(pattern, code):
            raise SecurityViolationError(f"Forbidden pattern detected: {desc}")


def is_safe(code: str, language: str = "python") -> bool:
    """非抛出版安全检查，返回 True/False。"""
    try:
        validate_code_safety(code, language)
        return True
    except SecurityViolationError:
        return False
