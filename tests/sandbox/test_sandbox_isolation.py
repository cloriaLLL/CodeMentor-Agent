"""隔离器选择与降级测试。"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from agents.sandbox_isolation import (
    DockerIsolator,
    ProcessTreeIsolator,
    RawResult,
    RunSpec,
    get_isolator,
    reset_isolator_cache,
)


def test_process_tree_always_available():
    assert ProcessTreeIsolator().available() is True


def test_docker_availability_is_bool():
    assert isinstance(DockerIsolator().available(), bool)


def test_get_isolator_prefers_process_tree_when_disabled():
    reset_isolator_cache()
    iso = get_isolator(prefer_docker=False)
    assert isinstance(iso, ProcessTreeIsolator)


def test_process_tree_runs_python():
    reset_isolator_cache()
    iso = get_isolator(prefer_docker=False)
    d = Path(tempfile.mkdtemp(prefix="iso_test_"))
    f = d / "s.py"
    f.write_text("print('ok')", encoding="utf-8")
    spec = RunSpec(
        cmd=[sys.executable, str(f)],
        cwd=d,
        timeout=10,
        env=os.environ.copy(),
        language="python",
        docker_image=None,
    )
    raw = iso.run(spec, f)
    assert isinstance(raw, RawResult)
    assert raw.timed_out is False
    assert raw.returncode == 0
    assert "ok" in raw.stdout
    assert raw.isolated_by == "process-tree"


def test_process_tree_timeout():
    reset_isolator_cache()
    iso = get_isolator(prefer_docker=False)
    d = Path(tempfile.mkdtemp(prefix="iso_to_"))
    f = d / "s.py"
    f.write_text("import time\ntime.sleep(5)", encoding="utf-8")
    spec = RunSpec(
        cmd=[sys.executable, str(f)],
        cwd=d,
        timeout=1,
        env=os.environ.copy(),
        language="python",
        docker_image=None,
    )
    raw = iso.run(spec, f)
    assert raw.timed_out is True


def test_isolator_cache_resets():
    reset_isolator_cache()
    iso1 = get_isolator(prefer_docker=False)
    iso2 = get_isolator(prefer_docker=False)
    assert iso1 is iso2  # 同一缓存实例
    reset_isolator_cache()
    iso3 = get_isolator(prefer_docker=False)
    assert iso3 is not iso1  # 重置后新建
