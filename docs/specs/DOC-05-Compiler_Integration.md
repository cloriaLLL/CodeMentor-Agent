# DOC-05: 通用简易编译器集成规范

> **文档定位**：CodeMentor Agent 通用简易编译器工具链集成规范
> **依据**：`PROJECT_REPORT.md` §2 现有架构、`DOC-02` 沙箱引擎、`DOC-04` 前端工作区
> **状态**：编译器集成 v1.0 设计
> **约束**：纯 Python 实现，零侵入接入现有沙箱与 DI 体系，不更换开发语言

---

## 1. 文档概述

本规范定义 CodeMentor Agent 集成"通用简易编译器"的完整方案，目标是在不更换任何现有开发语言（Python 3.12 后端 + TypeScript 前端）的前提下，引入一套可插拔的编译器工具链，为项目提供三项能力：

1. **快速编译能力**：单文件编译延迟 < 50ms（千行内），缓存命中 < 1ms
2. **基础 IDE 级代码提示**：语法高亮（已具备）、自动补全、错误诊断、悬停提示
3. **与现有架构无缝集成**：通过 `LanguageRuntime` 注册表、`AppContainer` 依赖注入、`Settings` 配置三处既有扩展点接入，零修改沙箱核心

### 1.1 "通用简易编译器"的精确定位

本编译器**不替代**现有 Java/C# 外部编译器，而是一套用 Python 实现的可插拔编译器工具链框架：

```
源代码（自定义教学语言 / MiniLang / DSL）
        │
        ▼
┌─────────────────────────────────────┐
│  通用简易编译器内核（Python 实现）    │
│  Lexer → Parser → AST → IR → Codegen │
└──────────────┬──────────────────────┘
               │ 产出目标代码（Python / JS / 自定义字节码）
               ▼
┌─────────────────────────────────────┐
│  现有沙箱引擎（无需改造，复用）      │
│  LanguageRuntime + Isolator + Security│
└─────────────────────────────────────┘
```

### 1.2 设计原则

1. **复用优先**：编译器产出的目标代码复用现有沙箱执行，不另建运行时
2. **零侵入扩展**：仅子类化 `LanguageRuntime`、新增 DI property、新增配置字段
3. **安全纵深**：输入验证 → AST 白名单 → 编译沙箱 → 产物二次校验，四层防御
4. **教学可用**：内置 MiniLang 教学语言，可直接用于编译原理教学闭环

### 1.3 MVP 裁剪方案

- ✅ 词法分析（规则表驱动 + 合并正则）
- ✅ 语法分析（递归下降 + Pratt 运算符优先级 + panic mode 错误恢复）
- ✅ 代码生成（AST → Python 源码直通，复用 PythonRuntime）
- ✅ AST 白名单安全校验
- ✅ IDE 语言服务（补全/诊断/悬停）
- ❌ 完整 SSA 中间表示与优化（预留 IR 抽象层，v2 实现）
- ❌ 自建字节码 VM（预留 codegen target，当前直通 Python）

---

## 2. 模块接口契约

### 2.1 编译器内核对外接口（compiler/compiler.py）

```python
def compile_source(
    source: str,
    language: str = "minilang",
    target: str = "python",
) -> CompileResult:
    """
    编译源代码到目标语言。
    返回 CompileResult，含目标代码、诊断、AST、耗时。
    """

@dataclass
class CompileResult:
    target_code: str                          # 产物代码
    diagnostics: list[Diagnostic]             # 编译期诊断（含警告与错误）
    ast: Program                               # 抽象语法树（IDE 复用）
    elapsed_sec: float
    from_cache: bool                           # 是否命中缓存
```

### 2.2 语言服务接口（agents/language_service/）

```python
def complete(source: str, cursor_offset: int, language: str) -> list[CompletionItem]: ...
def lint(source: str, language: str) -> list[Diagnostic]: ...
def hover(source: str, offset: int, language: str) -> str | None: ...
def signature_help(source: str, offset: int, language: str) -> SignatureHelp | None: ...
```

### 2.3 HTTP API 端点（app/api/compiler.py）

| 端点 | 方法 | 功能 | 调用方 |
|------|------|------|--------|
| `/api/compiler/compile` | POST | 编译源码（可选附带执行） | 前端运行按钮 |
| `/api/compiler/lint` | POST | 实时诊断（高频，防抖 150ms） | 编辑器诊断层 |
| `/api/compiler/complete` | POST | 自动补全 | 补全弹窗 |
| `/api/compiler/hover` | POST | 悬停提示 | 编辑器悬停 |
| `/api/compiler/interpret` | POST | 纯解释执行（REPL） | 教学场景 |

### 2.4 沙箱集成接口（agents/sandbox_runtime.py）

通过新增 `MiniLangRuntime(LanguageRuntime)` 子类并 `register()` 注册，自动获得：
- `/api/languages` 自动列出
- `/api/exercise/run` 自动支持运行
- `validate_code_safety` 安全校验
- `SandboxIsolator` 隔离执行

---

## 3. 编译器内核设计

### 3.1 词法分析器（compiler/lexer.py）

- **规则表驱动**：`TokenRule` 列表按 priority 排序，关键字优先于标识符
- **合并正则优化**：所有规则编译为单个 master 正则，一次 `match` 完成匹配
- **错误恢复**：非法字符记录 `ERROR` token 但继续扫描
- **时间复杂度**：O(n) 单遍扫描

```python
class Lexer:
    def __init__(self, rules: list[TokenRule], keywords: set[str]): ...
    def tokenize(self, source: str) -> list[Token]: ...
```

### 3.2 语法分析器（compiler/parser.py）

- **递归下降**处理语句级（声明、if、while、func、return）
- **Pratt parser**处理表达式（运算符优先级天然，避免左递归）
- **panic mode 错误恢复**：遇错同步到下一个语句边界（分号/换行）继续，一次编译产出所有诊断
- **AST 节点**：`@dataclass(frozen=True)` 不可变可哈希，便于缓存

### 3.3 代码生成器（compiler/codegen.py）

采用"AST → Python 源码"单遍直通策略：

```python
class PythonCodegen(CodegenTarget):
    def emit(self, ast: Program) -> str: ...
```

**字符串安全转义**：所有字符串字面量经 `repr()` 转义，杜绝字符串内代码注入。

### 3.4 编译缓存（compiler/compile_cache.py）

```python
key = sha256(language + source + target + spec_version)
@lru_cache(maxsize=256)
def _compile_cached(...) -> str: ...
```

### 3.5 语言规范层（compiler/lang/）

内置 MiniLang 教学语言：

```python
KEYWORDS = {"let", "print", "if", "else", "while", "func", "return", "true", "false"}
BUILTINS = {"print", "len", "range", "abs", "min", "max", "str", "int", "float"}
OPERATOR_PREC = {"+":1, "-":1, "*":2, "/":2, "%":2, "==":0, "!=":0, "<":0, ">":0}
SPEC_VERSION = "minilang-1.0"
```

语法示例：
```
let x = 10
let y = x * 2 + 1
func add(a, b) {
    return a + b
}
print(add(x, y))
```

---

## 4. IDE 语言服务设计

### 4.1 复用编译器前端

编译器前端的词法/语法分析天然支持 IDE 能力——自研编译器相比调外部 LSP 的核心优势。

### 4.2 三类补全源

1. **关键字补全**：输入 `l` → `let`
2. **内建函数补全**：输入 `p` → `print(`
3. **作用域符号补全**：解析当前文件已声明的变量/函数

### 4.3 一次性诊断

panic mode 错误恢复使一次编译返回**所有**错误，IDE 无需多次编译。

### 4.4 性能预算

| 操作 | 预算 |
|------|------|
| 补全响应 | < 30ms |
| 诊断延迟（防抖后） | < 100ms |
| 缓存命中 | < 1ms |

---

## 5. 安全加固设计（四层纵深防御）

### 5.1 第一层：输入验证（compiler/input_validator.py）

编译前对原始输入约束，防资源耗尽：
- 长度限制（默认 50000 字符）
- 嵌套深度预检（默认 64）
- 控制字符过滤（零宽字符 U+200B 等）
- 字符集白名单

### 5.2 第二层：AST 白名单（compiler/compiler_security.py）

**核心安全增强**——相比现有正则黑名单，AST 校验能识别：
- 字符串拼接构造危险调用：`__import__('o'+'s')`
- 动态属性访问：`getattr(os, 'system')`
- 禁止白名单外的函数调用
- 循环复杂度限制

```python
ALLOWED_NODES = {"Program", "NumberLit", "StringLit", "BooleanLit", "VarDecl",
                 "BinaryOp", "UnaryOp", "Call", "VarRef", "If", "While",
                 "Block", "Return", "FuncDecl"}
ALLOWED_CALLS = {"print", "len", "range", "abs", "min", "max", "str", "int", "float"}
```

### 5.3 第三层：编译沙箱（compiler/compile_sandbox.py）

限制编译过程本身：
- 编译超时（独立于执行超时，默认 5s）
- 递归深度限制（`sys.setrecursionlimit(256)` 局部）
- 子线程隔离（编译器崩溃不影响主服务）

### 5.4 第四层：编译产物二次校验

编译器产出的 Python 源码在交付沙箱前，复用现有 `validate_code_safety(产物, "python")` 做正则黑名单二次校验——确保即使编译器有 bug 生成危险代码，也无法执行。

### 5.5 代码注入防护矩阵

| 注入向量 | 防护层 |
|----------|--------|
| 字符串拼接 `__import__('o'+'s')` | AST 白名单禁止 `__import__` |
| 动态属性 `getattr(os,'system')` | AST 白名单不含 `getattr` |
| 字符串转义注入 | Codegen `repr()` 转义 + 产物二次校验 |
| 注释/字符串藏 payload | AST 结构校验 + 产物正则校验 |
| 编译器漏洞利用 | 编译沙箱超时 + 递归限制 |
| 巨型源码 OOM | 输入长度限制 |
| 深嵌套栈溢出 | 输入深度预检 + 编译递归限制 |

---

## 6. 与现有系统的集成

### 6.1 LanguageRuntime 扩展

```python
class MiniLangRuntime(LanguageRuntime):
    language = "minilang"
    aliases = ("ml", "mini")
    is_compiled = True
    def prepare(self, code_file, cwd):
        # .ml → .py，调用编译器内核
    def build_run_command(self, code_file, cwd):
        return [sys.executable, str(cwd / "compiled.py")]

register(MiniLangRuntime())
```

### 6.2 依赖注入接入

`AppContainer` 新增 `compiler_service` 懒加载 property（不改现有属性）。

### 6.3 配置接入

`Settings` 新增 `compiler_enabled`、`compiler_max_source_len`、`compiler_max_ast_depth`、`compiler_timeout`、`compiler_cache_size` 字段。

### 6.4 前端编辑器增强

在现有 [CodeEditor.tsx](file:///c:/WorkSpace/CodeMentor%20Agent/frontend/src/components/exercise/CodeEditor.tsx) 上叠加两层（不重写）：
- `DiagnosticsLayer`：错误下划线（pointer-events:none）
- `CompletionPopup`：补全候选弹窗

新增 `useLanguageService` Hook（防抖 150ms + AbortController 5s 超时，复刻现有模式）。

**不引入 Monaco Editor**——保持轻量，与项目定位一致。

---

## 7. 文件结构

```text
compiler/                          # 编译器内核（纯 Python）
├── __init__.py
├── lexer.py                       # 词法分析
├── parser.py                      # 语法分析
├── ast_nodes.py                   # AST 节点
├── ir.py                          # 中间表示（预留）
├── codegen.py                     # 代码生成
├── compiler.py                    # 流水线编排
├── compile_cache.py               # 哈希缓存
├── compiler_security.py           # AST 白名单
├── input_validator.py             # 输入验证
├── compile_sandbox.py              # 编译沙箱
├── diagnostics.py                 # 诊断模型
└── lang/
    ├── __init__.py
    ├── language_spec.py           # 语言规范基类
    └── minilang.py                # 教学语言

agents/
├── language_service/              # IDE 语言服务
│   ├── __init__.py
│   ├── language_service.py
│   ├── completion.py
│   ├── diagnostics_service.py
│   └── hover.py
└── sandbox_runtime.py             # 修改：新增 MiniLangRuntime

app/
├── api/compiler.py                # 新增 API 端点
├── services/compiler_service.py   # 编译器服务
├── core/{container,config,app_factory}.py  # 修改：增量接入
└── schemas/__init__.py             # 修改：新增模型

frontend/src/
├── hooks/useLanguageService.ts     # 语言服务 Hook
└── components/exercise/
    ├── CodeEditor.tsx              # 修改：叠加诊断层 + 补全弹窗
    ├── CompletionPopup.tsx          # 新增
    └── DiagnosticsLayer.tsx         # 新增

tests/
├── test_compiler_lexer.py
├── test_compiler_parser.py
├── test_compiler_security.py
├── test_compiler_codegen.py
└── test_compiler_api.py
```

---

## 8. 性能预算

| 操作 | 预算 | 优化手段 |
|------|------|----------|
| 千行编译 | < 50ms | 合并正则 + 单遍直通 |
| 缓存命中 | < 1ms | lru_cache(256) |
| 补全 | < 30ms | 复用前端 AST + 符号表 |
| 诊断 | < 100ms | panic mode 一次产出 |
| 编译超时 | 5s | 独立于执行超时 |
| 执行超时 | 10s | 复用现有 SANDBOX_TIMEOUT |

---

## 9. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 正则 ReDoS | 编译沙箱超时 + 原子组 |
| AST 白名单误报 | 白名单按语言独立配置 |
| 编译产物绕过沙箱 | 四层纵深 + 产物二次校验 |
| 语法变更破坏缓存 | SPEC_VERSION 机制自动失效 |
| 补全弹窗性能 | 防抖 150ms + AbortController |

---

## 10. 实施路径

| 阶段 | 内容 | 工期 |
|------|------|------|
| A | 规范文档（本文档） | 0.5 人天 |
| B | 编译器内核（lexer/parser/codegen/cache） | 2-3 人天 |
| C | 安全加固 + PoC 攻击向量测试 | 2 人天 |
| D | IDE 服务 + 沙箱集成 + API + 前端 | 5-6 人天 |
| **合计** | | **11-14 人天** |

---

> **规范结束**。后续实现严格依本规范执行。
