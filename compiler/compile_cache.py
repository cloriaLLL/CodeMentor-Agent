"""CodeMentor Agent — 编译缓存。

基于源码哈希的增量编译缓存：
- key = sha256(language + source + target + spec_version)
- lru_cache 自动缓存最近 N 次编译结果（进程内）
- 命中缓存直接返回目标代码，跳过词法/语法/代码生成全流程
- spec_version 变更时缓存自动失效（语言规范演进不污染旧缓存）

性能预算：
- 缓存命中 < 1ms
- IDE 实时诊断时同一份代码重复编译（每次按键触发）直接命中缓存

依据：DOC-05 §3.4 编译缓存
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Callable, TypeVar

T = TypeVar("T")


def cache_key(language: str, source: str, target: str, spec_version: str) -> str:
    """计算缓存 key（SHA-256）。

    参数包含 spec_version，保证语言规范演进时缓存自动失效。
    """
    raw = f"{language}|{target}|{spec_version}|{source}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CompileCache:
    """编译结果缓存。

    用 lru_cache 实现，进程内缓存，重启失效（可接受，因编译本身 < 50ms）。
    提供 get/set 抽象与命中率统计（便于调优）。
    """

    def __init__(self, maxsize: int = 256) -> None:
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0
        # 内部用 dict 模拟 LRU（lru_cache 装饰器不便动态调整 maxsize）
        self._store: dict[str, str] = {}
        self._order: list[str] = []

    def get(self, key: str) -> str | None:
        if key in self._store:
            # 移到末尾（最近使用）
            self._order.remove(key)
            self._order.append(key)
            self._hits += 1
            return self._store[key]
        self._misses += 1
        return None

    def set(self, key: str, value: str) -> None:
        if key in self._store:
            self._order.remove(key)
        self._store[key] = value
        self._order.append(key)
        # 淘汰最久未使用
        while len(self._order) > self._maxsize:
            old = self._order.pop(0)
            self._store.pop(old, None)

    def clear(self) -> None:
        """清空缓存（测试或 spec 变更时使用）。"""
        self._store.clear()
        self._order.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict:
        """返回命中率统计。"""
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "maxsize": self._maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": (self._hits / total) if total > 0 else 0.0,
        }


# 全局单例缓存（默认 256 条目，可由 config.compiler_cache_size 配置覆盖）
_global_cache = CompileCache(maxsize=256)


def get_cache() -> CompileCache:
    """获取全局编译缓存单例。"""
    return _global_cache


def set_cache_maxsize(maxsize: int) -> None:
    """调整全局缓存容量（启动时由 config 调用）。"""
    global _global_cache
    if maxsize != _global_cache._maxsize:
        _global_cache = CompileCache(maxsize=maxsize)
