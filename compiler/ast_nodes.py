"""CodeMentor Agent — 抽象语法树（AST）节点定义。

所有节点用 @dataclass(frozen=True)，不可变且可哈希：
- 可哈希 → 可作为缓存 key 的一部分
- 不可变 → 编译期诊断、安全校验期间不会被意外篡改
- 等值比较 → AST 结构相等即视为同一编译产物（缓存命中）

每个节点携带 line/column 用于：
1. IDE 诊断精确定位
2. 运行时错误回溯到源码位置

依据：DOC-05 §3.2 AST 节点定义
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    """AST 节点基类。所有节点携带源码位置信息。"""
    line: int = 0
    column: int = 0


# --------------------------------------------------------------------------- #
# 字面量
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class NumberLit(Node):
    """数字字面量。统一用 float 存储，代码生成时按需转 int。"""
    value: float = 0.0


@dataclass(frozen=True)
class StringLit(Node):
    """字符串字面量。原始值，转义在 codegen 阶段处理。"""
    value: str = ""


@dataclass(frozen=True)
class BooleanLit(Node):
    value: bool = False


# --------------------------------------------------------------------------- #
# 标识符与赋值
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class VarRef(Node):
    """变量引用（读取）。"""
    name: str = ""


@dataclass(frozen=True)
class VarDecl(Node):
    """变量声明：let name = value。"""
    name: str = ""
    value: "Node | None" = None


@dataclass(frozen=True)
class Assign(Node):
    """赋值：name = value（已有变量的重新赋值）。"""
    name: str = ""
    value: "Node | None" = None


# --------------------------------------------------------------------------- #
# 运算
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class BinaryOp(Node):
    """二元运算：left op right。op 为运算符字符串。"""
    op: str = ""
    left: "Node | None" = None
    right: "Node | None" = None


@dataclass(frozen=True)
class UnaryOp(Node):
    """一元运算：op operand。op 为 '-' 或 'not'。"""
    op: str = ""
    operand: "Node | None" = None


# --------------------------------------------------------------------------- #
# 调用与函数
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Param(Node):
    """函数参数定义。"""
    name: str = ""


@dataclass(frozen=True)
class Call(Node):
    """函数调用：callee(args...)。callee 为函数名。"""
    callee: str = ""
    args: tuple["Node", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FuncDecl(Node):
    """函数声明：func name(params) { body }。"""
    name: str = ""
    params: tuple[Param, ...] = field(default_factory=tuple)
    body: "Block | None" = None


# --------------------------------------------------------------------------- #
# 控制流
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Block(Node):
    """语句块：{ stmt1; stmt2; ... }。"""
    statements: tuple["Node", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class If(Node):
    """条件：if cond { then } else { else }。else_body 可为 None。"""
    condition: "Node | None" = None
    then_body: "Block | None" = None
    else_body: "Block | None" = None


@dataclass(frozen=True)
class While(Node):
    """循环：while cond { body }。"""
    condition: "Node | None" = None
    body: "Block | None" = None


@dataclass(frozen=True)
class Return(Node):
    """返回语句：return value。value 可为 None（裸 return）。"""
    value: "Node | None" = None


@dataclass(frozen=True)
class ExprStmt(Node):
    """表达式语句：独立表达式（如 print(x)）。"""
    expr: "Node | None" = None


# --------------------------------------------------------------------------- #
# 顶层
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Program(Node):
    """程序顶层：一组语句。"""
    statements: tuple["Node", ...] = field(default_factory=tuple)


def walk(node: Node) -> list[Node]:
    """深度优先遍历 AST，返回所有节点列表（含自身）。

    供安全校验与 IDE 服务遍历使用。不递归进入函数体的局部作用域
    会丢失符号——安全校验需扁平遍历全部节点，故这里全量展开。
    """
    result: list[Node] = [node]
    _collect_children(node, result)
    return result


def _collect_children(node: Node, out: list[Node]) -> None:
    """递归收集所有子节点。"""
    if isinstance(node, Program):
        for s in node.statements:
            out.append(s)
            _collect_children(s, out)
    elif isinstance(node, Block):
        for s in node.statements:
            out.append(s)
            _collect_children(s, out)
    elif isinstance(node, (VarDecl, Assign)):
        if node.value is not None:
            out.append(node.value)
            _collect_children(node.value, out)
    elif isinstance(node, BinaryOp):
        for child in (node.left, node.right):
            if child is not None:
                out.append(child)
                _collect_children(child, out)
    elif isinstance(node, UnaryOp):
        if node.operand is not None:
            out.append(node.operand)
            _collect_children(node.operand, out)
    elif isinstance(node, Call):
        for a in node.args:
            out.append(a)
            _collect_children(a, out)
    elif isinstance(node, FuncDecl):
        for p in node.params:
            out.append(p)
        if node.body is not None:
            out.append(node.body)
            _collect_children(node.body, out)
    elif isinstance(node, If):
        for child in (node.condition, node.then_body, node.else_body):
            if child is not None:
                out.append(child)
                _collect_children(child, out)
    elif isinstance(node, While):
        for child in (node.condition, node.body):
            if child is not None:
                out.append(child)
                _collect_children(child, out)
    elif isinstance(node, Return):
        if node.value is not None:
            out.append(node.value)
            _collect_children(node.value, out)
    elif isinstance(node, ExprStmt):
        if node.expr is not None:
            out.append(node.expr)
            _collect_children(node.expr, out)
