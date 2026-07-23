"""CodeMentor Agent — 中间表示（IR）抽象层（预留）。

当前版本采用"AST → Python 源码"单遍直通，不经过 IR。
本模块定义 IR 抽象基类与接口，供 v2 实现 SSA + 字节码 VM 优化时使用。

依据：DOC-05 §1.3 MVP 裁剪：预留 IR 抽象层
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from compiler.ast_nodes import Node, Program


class IRNode(ABC):
    """IR 节点基类（预留）。"""
    @abstractmethod
    def to_dict(self) -> dict: ...


class IRBuilder(ABC):
    """IR 构建器基类（预留）。

    v2 实现将 AST 转换为 SSA 形式 IR，支持：
    - 常量折叠
    - 死代码消除
    - 循环展开
    """
    @abstractmethod
    def build(self, ast: Program) -> Any:
        """AST → IR（未实现）。"""
        raise NotImplementedError("IR 优化未实现，当前直通 codegen")
