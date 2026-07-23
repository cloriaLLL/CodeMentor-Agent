"""CodeMentor Agent — 多语言运行时抽象与注册表。

为沙箱提供统一的语言运行时接口：每种语言实现一个 LanguageRuntime，
封装文件扩展名、运行/编译命令、可用性检测、是否支持测试框架、Docker 镜像等。

设计要点：
- sandbox_runtime 不依赖 sandbox / sandbox_security，避免循环导入。
- 注册表在模块加载时注册内置 runtime（python/javascript/bash/java/csharp）。
- 通过 get_runtime(language) 解析别名（py→python）并返回规范 runtime。

本机环境验证（2026-07-22）：Python 3.12 / Node / JDK 21 / dotnet 可用；bash 经实测探测
（WSL 发行版若损坏则判定为不可用，避免 system32\bash.exe 误报）。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from agents.sandbox_exceptions import UnsupportedLanguageError


@dataclass(frozen=True)
class RuntimeAvailability:
    """运行时可用性检测结果。"""
    installed: bool
    compiler_path: str | None = None
    runner_path: str | None = None
    version: str | None = None


class LanguageRuntime(ABC):
    """单语言运行时抽象基类。子类通过类属性声明元数据，实现命令构建方法。"""

    # —— 子类覆盖的类属性 —— #
    language: str = ""                 # 规范名，如 "python"
    aliases: tuple[str, ...] = ()      # 别名，如 ("py", "python3")
    display_name: str = ""             # 展示名，如 "Python"
    file_extension: str = ""           # 文件扩展名（含点），如 ".py"
    supports_tests: bool = False       # 是否接入测试框架（pytest/JUnit 等）
    is_compiled: bool = False          # 是否为编译型语言
    docker_image: str | None = None    # Docker 隔离所用镜像，None 表示仅本地

    @abstractmethod
    def check_availability(self) -> RuntimeAvailability:
        """检测本机运行时是否可用（解释器/编译器是否在 PATH）。"""

    @abstractmethod
    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        """构建运行命令。code_file 为代码文件绝对路径，cwd 为工作目录。"""

    def prepare(self, code_file: Path, cwd: Path) -> None:
        """编译/预处理钩子，默认无操作。编译型语言在此编译。
        抛出 subprocess.CalledProcessError 时由调用方捕获转为 ExecutionError。"""
        return None

    def build_test_command(self, cwd: Path, solution_file: Path, test_file: Path) -> list[str] | None:
        """构建测试命令；返回 None 表示该语言不支持测试框架。"""
        return None

    def sandbox_env_extras(self) -> dict[str, str]:
        """该语言需要的额外环境变量（合并进基础沙箱 env）。"""
        return {}


# --------------------------------------------------------------------------- #
# 内置运行时实现
# --------------------------------------------------------------------------- #

class PythonRuntime(LanguageRuntime):
    language = "python"
    aliases = ("py", "python3", "python2")
    display_name = "Python"
    file_extension = ".py"
    supports_tests = True
    is_compiled = False
    docker_image = "python:3.12-slim"

    def check_availability(self) -> RuntimeAvailability:
        return RuntimeAvailability(
            installed=True,
            runner_path=sys.executable,
            version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )

    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        return [sys.executable, str(code_file)]


class JavaScriptRuntime(LanguageRuntime):
    language = "javascript"
    aliases = ("js", "node", "nodejs")
    display_name = "JavaScript"
    file_extension = ".js"
    supports_tests = False
    is_compiled = False
    docker_image = "node:20-slim"

    def check_availability(self) -> RuntimeAvailability:
        node_path = shutil.which("node")
        version = None
        if node_path:
            try:
                r = subprocess.run(
                    [node_path, "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                version = r.stdout.strip() or None
            except Exception:
                pass
        return RuntimeAvailability(installed=bool(node_path), runner_path=node_path, version=version)

    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        node_path = shutil.which("node")
        if not node_path:
            raise UnsupportedLanguageError("Node.js 未安装，无法运行 JavaScript 代码")
        return [node_path, str(code_file)]


class BashRuntime(LanguageRuntime):
    language = "bash"
    aliases = ("sh", "shell", "shellscript")
    display_name = "Bash / Shell"
    file_extension = ".sh"
    supports_tests = False
    is_compiled = False
    docker_image = "bash:5"

    @staticmethod
    def _find_bash() -> str | None:
        # Windows 优先用 WSL bash.exe / Git Bash；Unix 直接 which bash/sh
        if sys.platform == "win32":
            for name in ("bash", "sh"):
                p = shutil.which(name)
                if p:
                    return p
            return None
        return shutil.which("bash") or shutil.which("sh")

    def check_availability(self) -> RuntimeAvailability:
        p = self._find_bash()
        if not p:
            return RuntimeAvailability(installed=False)
        # 实测探测：Windows 上 system32\bash.exe（WSL 启动器）可能存在，
        # 但 WSL 发行版未安装/损坏时仅凭 which 命中会误报可用。
        # 跑一条 echo 探针确认 bash 真能执行命令（与 JS 的 node --version 探测一致）。
        try:
            r = subprocess.run(
                [p, "-c", "echo __BASH_OK__"],
                capture_output=True, text=True, timeout=5,
            )
            installed = r.returncode == 0 and "__BASH_OK__" in (r.stdout or "")
        except Exception:
            installed = False
        return RuntimeAvailability(
            installed=installed, runner_path=p if installed else None
        )

    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        p = self._find_bash()
        if not p:
            raise UnsupportedLanguageError("未找到 bash/sh，无法运行 Shell 代码")
        return [p, str(code_file)]


class JavaRuntime(LanguageRuntime):
    """Java 运行时。源文件固定为 Main.java（类名必须为 Main）。

    编译型：prepare() 跑 javac 生成 Main.class（输出到 cwd），
    build_run_command() 返回 `java Main`（依赖 cwd 定位 class 文件）。
    """
    language = "java"
    aliases = ("jsp",)
    display_name = "Java"
    file_extension = ".java"
    supports_tests = False
    is_compiled = True
    docker_image = "eclipse-temurin:21-jdk"
    main_class = "Main"

    def check_availability(self) -> RuntimeAvailability:
        java_path = shutil.which("java")
        javac_path = shutil.which("javac")
        return RuntimeAvailability(
            installed=bool(java_path and javac_path),
            compiler_path=javac_path,
            runner_path=java_path,
        )

    def prepare(self, code_file: Path, cwd: Path) -> None:
        javac = shutil.which("javac")
        if not javac:
            raise UnsupportedLanguageError("javac 未安装，无法编译 Java 代码")
        r = subprocess.run(
            [javac, str(code_file)],
            cwd=str(cwd), capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, [javac, str(code_file)], r.stdout, r.stderr)

    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        java = shutil.which("java")
        if not java:
            raise UnsupportedLanguageError("java 未安装，无法运行 Java 代码")
        return [java, self.main_class]


class CSharpRuntime(LanguageRuntime):
    """C# (.NET) 运行时。源文件固定为 Program.cs，附最小 csproj。

    编译型：prepare() 生成 csproj 并 dotnet build，
    build_run_command() 返回 `dotnet run --no-build`（依赖 cwd）。
    每次构建约 2-3s，属编译型开销。
    """
    language = "csharp"
    aliases = ("cs", "c#", "dotnet")
    display_name = "C# (.NET)"
    file_extension = ".cs"
    supports_tests = False
    is_compiled = True
    docker_image = "mcr.microsoft.com/dotnet/sdk:8.0"
    project_name = "CodeMentorRun"

    def check_availability(self) -> RuntimeAvailability:
        dotnet = shutil.which("dotnet")
        return RuntimeAvailability(
            installed=bool(dotnet),
            compiler_path=dotnet,
            runner_path=dotnet,
        )

    def prepare(self, code_file: Path, cwd: Path) -> None:
        dotnet = shutil.which("dotnet")
        if not dotnet:
            raise UnsupportedLanguageError("dotnet 未安装，无法编译 C# 代码")
        csproj = cwd / f"{self.project_name}.csproj"
        csproj.write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            '  <PropertyGroup>\n'
            '    <OutputType>Exe</OutputType>\n'
            '    <TargetFramework>net8.0</TargetFramework>\n'
            '    <Nullable>disable</Nullable>\n'
            '    <ImplicitUsings>enable</ImplicitUsings>\n'
            '  </PropertyGroup>\n'
            '</Project>\n',
            encoding="utf-8",
        )
        r = subprocess.run(
            [dotnet, "build", str(csproj), "-c", "Release", "--nologo", "-v", "q"],
            cwd=str(cwd), capture_output=True, text=True,
        )
        if r.returncode != 0:
            raise subprocess.CalledProcessError(r.returncode, [dotnet, "build"], r.stdout, r.stderr)

    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        dotnet = shutil.which("dotnet")
        if not dotnet:
            raise UnsupportedLanguageError("dotnet 未安装，无法运行 C# 代码")
        return [dotnet, "run", "--project", self.project_name, "--no-build", "-c", "Release"]


class MiniLangRuntime(LanguageRuntime):
    """MiniLang 教学语言运行时（DOC-05 编译器集成）。

    设计：编译到 Python 源码后复用 PythonRuntime 执行。
    - is_compiled=True，走 prepare() 编译钩子
    - prepare() 调用编译器内核将 .ml 编译为 .py
    - build_run_command() 返回 python 解释器命令执行产物
    - 隔离执行、安全校验全部复用现有沙箱

    注册后自动获得 /api/languages 列表与 /api/exercise/run 支持。
    """
    language = "minilang"
    aliases = ("ml", "mini")
    display_name = "MiniLang（教学语言）"
    file_extension = ".ml"
    supports_tests = False
    is_compiled = True              # 走编译路径（prepare 钩子）
    docker_image = None             # 复用 Python 镜像（若启用 Docker）

    def prepare(self, code_file: Path, cwd: Path) -> None:
        """编译 MiniLang 源码到 Python。

        调用编译器内核：.ml → .py，写入 compiled.py。
        四层安全防御由 CompilerService 在更上层调用时保证；
        此处仅做纯编译（已通过输入验证与 AST 校验的代码才会到达）。
        """
        # 延迟导入避免模块加载时开销
        from compiler import compile_source
        from compiler.compiler_security import (
            CompilerSecurityError, check_ast_safety,
        )
        from compiler.input_validator import (
            InputValidationError, validate_input,
        )
        from agents.sandbox_exceptions import ExecutionError, SecurityViolationError

        source = code_file.read_text(encoding="utf-8")
        # 输入验证（防御性，正常路径上层已校验）
        try:
            validate_input(source)
        except InputValidationError as e:
            raise ExecutionError(f"MiniLang 输入验证失败：{e}")
        # 编译（跳过缓存，因文件内容可能变化）
        result = compile_source(source, language="minilang", target="python",
                                skip_cache=True, return_ast=True)
        if result.has_error:
            msgs = "; ".join(d.message for d in result.diagnostics
                             if d.severity == "error")
            raise ExecutionError(f"MiniLang 编译失败：{msgs}")
        # AST 安全校验（转为沙箱安全异常，便于 /exercise/run 统一捕获）
        if result.ast is not None:
            try:
                check_ast_safety(result.ast)
            except CompilerSecurityError as e:
                raise SecurityViolationError(f"MiniLang 安全校验失败：{e}")
        # 写入产物
        target_path = cwd / "compiled.py"
        target_path.write_text(result.target_code, encoding="utf-8")

    def build_run_command(self, code_file: Path, cwd: Path) -> list[str]:
        """返回执行编译产物的命令。"""
        return [sys.executable, str(cwd / "compiled.py")]

    def check_availability(self) -> "RuntimeAvailability":
        """MiniLang 编译器是纯 Python 内置，恒可用。"""
        return RuntimeAvailability(installed=True, version="1.0")


# --------------------------------------------------------------------------- #
# 注册表
# --------------------------------------------------------------------------- #

_REGISTRY: dict[str, LanguageRuntime] = {}
_ALIAS_MAP: dict[str, str] = {}


def register(runtime: LanguageRuntime) -> None:
    """注册一个运行时（按规范名 + 别名登记）。"""
    canonical = runtime.language.lower()
    _REGISTRY[canonical] = runtime
    _ALIAS_MAP[canonical] = canonical
    for alias in runtime.aliases:
        _ALIAS_MAP[alias.lower()] = canonical


def get_runtime(language: str) -> LanguageRuntime:
    """按规范名或别名获取运行时。未知语言抛 UnsupportedLanguageError。"""
    if not language:
        raise UnsupportedLanguageError("language 为空")
    canonical = _ALIAS_MAP.get(language.lower())
    if not canonical:
        raise UnsupportedLanguageError(
            f"不支持的语言：{language}。当前支持：{sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[canonical]


def list_runtimes() -> list[LanguageRuntime]:
    """返回所有已注册运行时（按规范名排序）。"""
    return [_REGISTRY[k] for k in sorted(_REGISTRY.keys())]


def resolve_language(language: str) -> str:
    """将别名解析为规范名；未知则原样返回（由 get_runtime 在使用时拒绝）。"""
    return _ALIAS_MAP.get((language or "").lower(), (language or "").lower())


# 模块加载时注册内置运行时
register(PythonRuntime())
register(JavaScriptRuntime())
register(BashRuntime())
register(JavaRuntime())
register(CSharpRuntime())
register(MiniLangRuntime())   # DOC-05 编译器集成：MiniLang → Python
