"""CodeMentor Agent — 沙箱隔离抽象（Docker 首选 + 进程树降级）。

提供统一的 SandboxIsolator 接口执行外部命令：
- DockerIsolator：在临时容器内执行，网络隔离 + 资源限制（首选）。
- ProcessTreeIsolator：本地进程树执行，超时杀整个进程组（降级，恒可用）。

Docker daemon 不可用时自动降级到进程树隔离，保证沙箱永不不可用。

Docker 容器约束：
- --network=none         无网络
- --memory=256m --cpus=1.0 --pids-limit=64   资源限制
- 代码目录只读挂载到 /work，工作目录 /work
- --tmpfs /tmp           容器内可写临时目录
- --rm                   执行后自动清理容器
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger

logger = get_logger(__name__)

# 输出截断阈值（与 sandbox.py 一致，1MB）
_MAX_OUTPUT_BYTES = 1_000_000


def _truncate(text: str) -> str:
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_OUTPUT_BYTES:
        return text
    return encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace") + "\n... [truncated]"


@dataclass
class RunSpec:
    """单次执行规格。"""
    cmd: list[str]
    cwd: Path
    timeout: int
    env: dict
    language: str = "python"
    docker_image: Optional[str] = None   # 若非 None 且 Docker 可用，优先容器执行


@dataclass
class RawResult:
    """原始执行结果（与具体语言无关）。"""
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    elapsed: float
    isolated_by: str = "process-tree"   # "docker" | "process-tree"


class SandboxIsolator(ABC):
    """隔离执行器抽象基类。"""

    @abstractmethod
    def available(self) -> bool:
        """该隔离器在当前环境是否可用。"""

    @abstractmethod
    def run(self, spec: RunSpec, code_file: Path) -> RawResult:
        """按规格执行命令，返回原始结果。code_file 用于容器挂载定位。"""


# --------------------------------------------------------------------------- #
# 进程树隔离（降级，恒可用）
# --------------------------------------------------------------------------- #

class ProcessTreeIsolator(SandboxIsolator):
    """本地进程树执行：超时杀整个进程组。"""

    def available(self) -> bool:
        return True

    def run(self, spec: RunSpec, code_file: Path) -> RawResult:
        start = time.time()
        popen_kwargs: dict = {
            "cwd": str(spec.cwd),
            "env": spec.env,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if sys.platform == "win32":
            # Windows: 新进程组，便于 taskkill /T 杀整树
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        try:
            proc = subprocess.Popen(spec.cmd, **popen_kwargs)
        except FileNotFoundError as e:
            return RawResult(
                returncode=-1, stdout="", stderr=str(e),
                timed_out=False, elapsed=time.time() - start, isolated_by="process-tree",
            )

        try:
            stdout, stderr = proc.communicate(timeout=spec.timeout)
            elapsed = time.time() - start
            return RawResult(
                returncode=proc.returncode if proc.returncode is not None else -1,
                stdout=_truncate(stdout or ""),
                stderr=_truncate(stderr or ""),
                timed_out=False,
                elapsed=elapsed,
                isolated_by="process-tree",
            )
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc.pid)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
            elapsed = time.time() - start
            return RawResult(
                returncode=-1,
                stdout=_truncate(stdout or ""),
                stderr=_truncate(stderr or "") + f"\n[执行超时（{spec.timeout}s 限制）]",
                timed_out=True,
                elapsed=elapsed,
                isolated_by="process-tree",
            )


def _kill_process_tree(pid: int) -> None:
    """杀整个进程树。Windows 用 taskkill /T /F；Unix 用 killpg。"""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        else:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception as e:
        logger.warning("kill_process_tree_failed", pid=pid, error=str(e))


# --------------------------------------------------------------------------- #
# Docker 隔离（首选）
# --------------------------------------------------------------------------- #

class DockerIsolator(SandboxIsolator):
    """Docker 容器执行：网络隔离 + 内存/CPU/进程数限制。"""

    def available(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            r = subprocess.run(
                ["docker", "info"],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _ensure_image(self, image: str) -> bool:
        """确保镜像存在，不存在则拉取。拉取失败返回 False。"""
        try:
            r = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True, timeout=15,
            )
            if r.returncode == 0:
                return True
        except Exception:
            pass
        logger.info("docker_pulling_image", image=image)
        try:
            r = subprocess.run(
                ["docker", "pull", image],
                capture_output=True, text=True, timeout=180,
            )
            if r.returncode != 0:
                logger.warning("docker_pull_failed", image=image, stderr=r.stderr[:300])
                return False
            return True
        except Exception as e:
            logger.warning("docker_pull_failed", image=image, error=str(e))
            return False

    def run(self, spec: RunSpec, code_file: Path) -> RawResult:
        image = spec.docker_image
        if not image:
            # 无镜像要求 → 退化为进程树
            return ProcessTreeIsolator().run(spec, code_file)

        # 镜像不存在则拉取，失败则降级进程树
        if not self._ensure_image(image):
            logger.warning("docker_image_unavailable_fallback", image=image)
            return ProcessTreeIsolator().run(spec, code_file)

        start = time.time()
        sandbox_dir = code_file.parent.resolve()
        rel_code = code_file.name
        work_dir = "/work"
        container_cmd = self._remap_cmd_for_container(spec.cmd, code_file, work_dir, rel_code)

        docker_cmd = [
            "docker", "run", "--rm",
            "--network=none",
            "--memory=256m",
            "--cpus=1.0",
            "--pids-limit=64",
            "--tmpfs", "/tmp:rw,size=64m",
            "-v", f"{sandbox_dir}:/work:ro",
            "-w", work_dir,
            image,
        ] + container_cmd

        try:
            proc = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            return ProcessTreeIsolator().run(spec, code_file)

        try:
            stdout, stderr = proc.communicate(timeout=spec.timeout)
            elapsed = time.time() - start
            return RawResult(
                returncode=proc.returncode if proc.returncode is not None else -1,
                stdout=_truncate(stdout or ""),
                stderr=_truncate(stderr or ""),
                timed_out=False,
                elapsed=elapsed,
                isolated_by="docker",
            )
        except subprocess.TimeoutExpired:
            # 超时：终止进程，--rm 会让容器自动清理
            try:
                proc.terminate()
                try:
                    proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate(timeout=3)
            except Exception:
                pass
            elapsed = time.time() - start
            return RawResult(
                returncode=-1,
                stdout="",
                stderr=f"[执行超时（{spec.timeout}s 限制），容器已停止]",
                timed_out=True,
                elapsed=elapsed,
                isolated_by="docker",
            )

    @staticmethod
    def _remap_cmd_for_container(
        cmd: list[str], code_file: Path, work_dir: str, rel_code: str
    ) -> list[str]:
        """将宿主命令重映射为容器内命令（把沙箱目录内绝对路径替换为 /work/<相对路径>）。

        对编译型语言（java Main / dotnet run --project X）保留其语义：
        这些参数非绝对路径，原样保留，容器内 cwd=/work 可正确定位。
        """
        sandbox_dir = code_file.parent.resolve()
        remapped: list[str] = []
        for arg in cmd:
            # 替换代码文件绝对路径
            if arg in (str(code_file), str(code_file.resolve())):
                remapped.append(f"{work_dir}/{rel_code}")
                continue
            # 替换沙箱目录内的其他绝对路径
            try:
                p = Path(arg)
                if p.is_absolute():
                    try:
                        rel = p.relative_to(sandbox_dir)
                        remapped.append(f"{work_dir}/{rel.as_posix()}")
                        continue
                    except ValueError:
                        pass
            except Exception:
                pass
            remapped.append(arg)
        return remapped


# --------------------------------------------------------------------------- #
# 选择器
# --------------------------------------------------------------------------- #

_isolator_cache: dict[str, SandboxIsolator] = {}


def get_isolator(prefer_docker: bool = True) -> SandboxIsolator:
    """获取隔离器。Docker 可用且 prefer_docker 时返回 DockerIsolator，否则进程树。

    结果缓存，避免每次执行都检测 docker info。
    """
    key = "docker" if prefer_docker else "process-tree"
    if key in _isolator_cache:
        return _isolator_cache[key]

    if prefer_docker:
        docker = DockerIsolator()
        if docker.available():
            logger.info("sandbox_isolator_selected", isolator="docker")
            _isolator_cache[key] = docker
            return docker
        logger.info("sandbox_isolator_fallback", reason="docker unavailable", isolator="process-tree")

    pt = ProcessTreeIsolator()
    _isolator_cache[key] = pt
    return pt


def reset_isolator_cache() -> None:
    """重置隔离器缓存（测试用，模拟 Docker 状态变化）。"""
    _isolator_cache.clear()
