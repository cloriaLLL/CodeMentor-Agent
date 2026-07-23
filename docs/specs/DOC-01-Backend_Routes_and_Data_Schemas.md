# DOC-01: Backend Routes and Data Schemas Specification

> **文档定位**：CodeMentor Agent MVP 后端路由层与数据契约层规范
> **依据**：`Demo设计.md` §2.2 API 契约 + §4 数据 Schema；`最终成品设计.md` §4 全量数据结构
> **状态**：Session 0 规范确立
> **约束**：本规范所有字段严格匹配设计文档，禁止凭空捏造未约定字段

---

## 1. 文档概述

本规范定义 CodeMentor Agent MVP 阶段的 FastAPI 后端服务，包含：
- FastAPI 应用初始化与中间件配置
- 4 个 RESTful API 端点的详细契约
- Pydantic 请求/响应数据模型
- `schemas/seed_data.json` 全量静态数据结构
- 统一错误响应格式

### 1.1 黄金闭环链路
```
装饰器 (Decorator)
    → @rate_limit 限流装饰器 Mini-Project
    → FastAPI + Redis 生态收尾
```

### 1.2 三状态机
- `TeachMode` — 概念讲解与历史演进
- `PracticeMode` — 双 Agent 出题与用户提交判题
- `EcosystemMode` — 工业栈定位与跨语言对比

### 1.3 内容来源约束（Content Source Constraint）⚠️ 重要

**所有展示给用户的文本内容必须来自以下两种合法来源之一，严禁在 Python 代码中硬编码：**

1. **预置数据文件**（MVP 阶段）— `schemas/seed_data.json`
   - 教学内容：`knowledge_atoms[].teach_content.markdown_content`
   - 题目说明：`seed_problems[].problem_statement`
   - 生态总结：`knowledge_atoms[].ecosystem_mapping.stack_summary`
   - 符合 Demo设计.md §1.1「采用预置 Markdown 文件及 JSON 元数据」允许的预置数据形式

2. **LLM 动态生成**（生产环境）— 基于 `prompts/*.txt` System Prompt 调用
   - Generator Agent 调用 LLM 生成变体题目
   - Orchestrator 调用 LLM 生成教学内容
   - Validator 调用 LLM 检查边界覆盖

**禁止行为：**
- ❌ 在 `main.py` 中硬编码任何教学内容、题目说明、生态总结文本
- ❌ 在 `agents/*.py` 中拼接假的 Markdown 内容（如 f-string 模板化生成）
- ❌ 在 Python 代码中嵌入假的对话响应

**合法行为：**
- ✅ 从 `seed_data.json` 读取预置字段
- ✅ 调用 LLM 基于 Prompt 生成内容
- ✅ 前端 UI 文案（如「正在生成...」「提交代码」按钮文本）属于 UI 反馈，不属于假问答

---

## 2. 文件归属与目录结构

```
codementor-mvp/
├── main.py                  # FastAPI 入口 + 4 个路由 + Pydantic 模型 + 中间件
├── schemas/
│   └── seed_data.json       # 预置装饰器知识元 + 种子题库 + 默认用户画像
└── app/requirements.txt     # 依赖：fastapi, uvicorn, pytest, requests, pydantic
```

**职责边界：**
- `main.py` 仅负责 HTTP 通信、请求校验、路由分发
- Agent 业务逻辑（Orchestrator/Generator/Validator）独立于 `agents/` 目录（见 DOC-03）
- 沙盒执行逻辑独立于 `sandbox.py`（见 DOC-02）
- `main.py` 通过函数调用方式与 `agents/` 和 `sandbox.py` 解耦

---

## 3. FastAPI 应用初始化规范

### 3.1 应用实例
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="CodeMentor Agent MVP",
    description="学→练→用 标准化节拍学习智能体",
    version="0.1.0",
)
```

### 3.2 CORS 中间件
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # MVP 阶段开放，生产环境需收紧
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 3.3 静态文件挂载
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### 3.4 全局异常处理器
捕获所有未处理异常，返回结构化错误 JSON（禁止暴露原始 Traceback）：
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "code": 500,
            "detail": str(exc)  # MVP 阶段保留 detail 便于调试，生产环境移除
        }
    )
```

---

## 4. Pydantic 数据模型定义

### 4.1 请求模型 (Request Models)

```python
from pydantic import BaseModel, Field
from typing import Optional

# === /api/teach 请求 ===
class TeachRequest(BaseModel):
    node_id: str = Field(..., description="知识节点 ID", examples=["python.advanced.decorator"])
    action: str = Field(..., description="动作类型", examples=["start"])

# === /api/generate_exercise 请求 ===
class GenerateExerciseRequest(BaseModel):
    node_id: str = Field(..., description="知识节点 ID")

# === /api/submit_code 请求 ===
class SubmitCodeRequest(BaseModel):
    exercise_id: str = Field(..., description="练习 ID")
    user_code: str = Field(..., description="用户提交的 Python 代码")

# === /api/ecosystem_summary 请求 ===
class EcosystemSummaryRequest(BaseModel):
    node_id: str = Field(..., description="知识节点 ID")
```

### 4.2 响应模型 (Response Models)

```python
# === /api/teach 响应 ===
class TeachResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    state: str = Field(..., examples=["TeachMode"])
    markdown_content: str = Field(..., description="Markdown 教学内容")
    grounding_source: str = Field(..., description="基准源名称")
    history_notes: str = Field(..., description="历史演进说明")
    next_actions: list[str] = Field(..., description="可选下一步动作")

# === /api/generate_exercise 响应 ===
class GenerateExerciseResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    exercise_id: str = Field(..., examples=["ex_decorator_rate_limit"])
    problem_statement: str = Field(..., description="题目说明（Markdown）")
    starter_code: str = Field(..., description="起始代码骨架")
    validator_status: str = Field(..., examples=["PASSED_ZERO_BROKEN"])

# === /api/submit_code 响应 ===
class SubmitCodeResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    passed: bool = Field(..., description="是否通过测试")
    score: int = Field(..., ge=0, le=100, description="得分 0-100")
    pytest_output: str = Field(..., description="pytest 输出文本")
    next_state: str = Field(..., examples=["EcosystemMode"])

# === /api/ecosystem_summary 响应 ===
class CrossLanguageEquivalent(BaseModel):
    Go: str = Field(..., examples=["Gin 框架 Middleware (HandlerFunc 链)"])

class EcosystemSummaryResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    state: str = Field(..., examples=["EcosystemMode"])
    stack_summary: str = Field(..., description="工业栈总结")
    cross_language_equivalent: CrossLanguageEquivalent
    next_node_recommendation: str = Field(..., examples=["python.advanced.asyncio"])
```

### 4.3 错误响应模型

```python
class ErrorResponse(BaseModel):
    status: str = Field("error", const=True)
    message: str = Field(..., description="人类可读错误信息")
    code: int = Field(..., ge=400, le=599, description="HTTP 状态码")
```

**错误码约定：**
| Code | 场景 |
|------|------|
| 400 | 请求参数校验失败（Pydantic ValidationError） |
| 404 | 节点/练习不存在 |
| 422 | Generator-Validator 重试 3 次仍失败 |
| 500 | 沙盒执行异常或未捕获错误 |

---

## 5. API 路由契约（4 个端点详细规范）

### 5.1 POST `/api/teach` — 教学对话与知识讲解（State 1: TeachMode）

**职责：** 读取 RAG 知识元，返回概念定义 + 历史演进 + 工业最小代码示例

**请求 Payload：**
```json
{
  "node_id": "python.advanced.decorator",
  "action": "start"
}
```

**响应 Payload：**
```json
{
  "status": "success",
  "state": "TeachMode",
  "markdown_content": "# Python 装饰器与高阶函数\n...",
  "grounding_source": "PEP 318 -- Decorators for Functions and Methods",
  "history_notes": "Python 2.4 正式引入 @ 语法糖...",
  "next_actions": ["go_to_practice", "more_examples"]
}
```

**处理逻辑：**
1. 从 `schemas/seed_data.json` 读取 `node_id` 对应的 `knowledge_atoms[]` 知识元
2. 返回 `markdown_content`（直接读取 `teach_content.markdown_content` 预置字段，禁止代码硬编码）
3. 返回 `grounding_source`（读取 `grounding_doc.source_name`）
4. 返回 `history_notes`（读取 `evolution_history.key_changes`）
5. 返回 `next_actions`（读取 `teach_content.next_actions`）

**错误场景：**
- `node_id` 不存在 → `404 {"status":"error","message":"Node not found","code":404}`

---

### 5.2 POST `/api/generate_exercise` — 双 Agent 实战出题（State 2: PracticeMode）

**职责：** 调用 Generator + Validator 双 Agent 生成并通过校验的练习题

**请求 Payload：**
```json
{
  "node_id": "python.advanced.decorator"
}
```

**响应 Payload：**
```json
{
  "status": "success",
  "exercise_id": "ex_decorator_rate_limit",
  "problem_statement": "请实现带参数的限流装饰器 @rate_limit(max_calls=3, period=60)...",
  "starter_code": "def rate_limit(max_calls: int, period: int):\n    # 请补全代码\n    pass\n",
  "validator_status": "PASSED_ZERO_BROKEN"
}
```

**处理逻辑（严格匹配 Demo设计.md §2.2 接口 2）：**
1. 调用 Generator Agent 从 `seed_data.json` 的 `seed_problems[]` 读取预置题目（`problem_statement`、`code_skeleton`、`reference_solution`、`test_cases` 全部从数据文件读取，禁止代码硬编码）
2. 调用 Validator Agent，将 `reference_solution` 与 `test_cases` 写入临时目录并调用 `sandbox.py` 执行
3. 若通过，返回生成结果；若失败，捕获 Traceback 并自动 Retry（上限 3 次）
4. 3 次仍失败 → 返回 `422 {"status":"error","message":"Generator-Validator retry exhausted","code":422}`

**`validator_status` 字段取值：**
- `PASSED_ZERO_BROKEN` — 校验通过，零坏题
- `RETRY_EXHAUSTED` — 重试耗尽（此场景应返回 error 状态）

---

### 5.3 POST `/api/submit_code` — 用户代码提交与判题

**职责：** 沙盒执行用户代码，运行 pytest，返回得分与下一状态

**请求 Payload：**
```json
{
  "exercise_id": "ex_decorator_rate_limit",
  "user_code": "import time\nfrom functools import wraps\n..."
}
```

**响应 Payload：**
```json
{
  "status": "success",
  "passed": true,
  "score": 100,
  "pytest_output": "3 passed in 0.02s",
  "next_state": "EcosystemMode"
}
```

**处理逻辑：**
1. 从 `seed_data.json` 读取 `exercise_id` 对应的 `test_cases`
2. 调用 `sandbox.py` 在临时目录执行 `user_code + test_cases`
3. 解析 pytest 输出，计算 `score`（通过率 × 100）
4. `passed=true` → `next_state="EcosystemMode"`；`passed=false` → `next_state="PracticeMode"`（重试）

**`score` 计算规则：**
```
score = (passed_tests / total_tests) * 100
```

---

### 5.4 POST `/api/ecosystem_summary` — 生态收尾与总结（State 3: EcosystemMode）

**职责：** 输出工业栈定位 + 跨语言对比 + 下一节点推荐

**请求 Payload：**
```json
{
  "node_id": "python.advanced.decorator"
}
```

**响应 Payload：**
```json
{
  "status": "success",
  "state": "EcosystemMode",
  "stack_summary": "在 FastAPI + Redis 架构中，装饰器常作为路由中间件与限流器使用...",
  "cross_language_equivalent": {
    "Go": "Gin 框架 Middleware (HandlerFunc 链)"
  },
  "next_node_recommendation": "python.advanced.asyncio"
}
```

**处理逻辑：**
1. 从 `seed_data.json` 读取 `node_id` 对应的 `knowledge_atoms[].ecosystem_mapping`
2. 返回 `stack_summary`（直接读取 `ecosystem_mapping.stack_summary` 预置字段，禁止代码硬编码）
3. 返回 `cross_language_equivalent`（读取 `ecosystem_mapping.cross_language_equivalents`）
4. 返回 `next_node_recommendation`（固定推荐 `python.advanced.asyncio`）

---

## 6. seed_data.json 全量数据结构

### 6.1 顶层结构

```json
{
  "knowledge_atoms": [...],
  "seed_problems": [...],
  "learner_profile": {...}
}
```

### 6.2 知识元 (knowledge_atom) — 严格匹配 最终成品设计.md §4.1

```json
{
  "node_id": "python.advanced.decorator",
  "language": "python",
  "title": "Python 装饰器与高阶函数",
  "category": "advanced",
  "prerequisites": ["python.basics.closure", "python.basics.function"],
  "grounding_doc": {
    "source_name": "PEP 318 -- Decorators for Functions and Methods",
    "url_or_pep": "https://peps.python.org/pep-0318/",
    "raw_text": "PEP 318 原文摘录..."
  },
  "evolution_history": {
    "introduced_version": "Python 2.4",
    "key_changes": "Python 2.4 正式引入 @ 语法糖；Python 3.9 增加类装饰器增强；Python 3.10+ 引入 ParamSpec 改进装饰器类型标注",
    "deprecated_features": "无显著废弃特性"
  },
  "ecosystem_mapping": {
    "primary_stack": "FastAPI + Redis",
    "industrial_use_case": "路由中间件、限流器、缓存装饰、依赖注入",
    "stack_summary": "在 FastAPI + Redis 架构中，装饰器常作为路由中间件与限流器使用。FastAPI 的 Depends() 依赖注入机制本质上就是装饰器模式的应用；Redis 配合装饰器可实现分布式限流（如 slowapi 框架）；中间件链式调用（@app.middleware）也是装饰器的工业实践。",
    "cross_language_equivalents": {
      "Go": "Gin 框架 Middleware (HandlerFunc 链)",
      "Java": "Spring AOP (@Aspect 注解)",
      "JavaScript": "Express Middleware (next() 链)"
    }
  },
  "teach_content": {
    "markdown_content": "# Python 装饰器与高阶函数\n\n## 1. 核心概念定义\n装饰器是...",
    "next_actions": ["go_to_practice", "more_examples"]
  }
}
```

### 6.3 种子题库 (seed_problem) — 严格匹配 最终成品设计.md §4.2 + MVP 扩展 problem_statement

```json
{
  "seed_id": "seed_decorator_rate_limit",
  "associated_node_id": "python.advanced.decorator",
  "difficulty": "Medium",
  "source_repository": "internal",
  "problem_statement": "请实现带参数的限流装饰器 `@rate_limit(max_calls=3, period=60)`，在指定时间窗口（period 秒）内允许最多 max_calls 次函数调用，超出限制时抛出 `RuntimeError('Rate limit exceeded')`。\n\n## 要求\n1. 必须使用 `functools.wraps` 保留原函数元信息\n2. 时间窗口滚动计算（基于调用时间戳）\n3. 线程安全可不考虑（MVP 单线程）\n\n## 函数签名\n```python\ndef rate_limit(max_calls: int, period: int):\n    def decorator(func):\n        ...\n    return decorator\n```\n\n## 评分\n通过全部 pytest 测试用例即得 100 分",
  "code_skeleton": "def rate_limit(max_calls: int, period: int):\n    # 请补全代码\n    pass\n",
  "reference_solution": "import time\nfrom functools import wraps\n\ndef rate_limit(max_calls: int, period: int):\n    def decorator(func):\n        calls = []\n        @wraps(func)\n        def wrapper(*args, **kwargs):\n            now = time.time()\n            calls[:] = [t for t in calls if now - t < period]\n            if len(calls) >= max_calls:\n                raise RuntimeError('Rate limit exceeded')\n            calls.append(now)\n            return func(*args, **kwargs)\n        return wrapper\n    return decorator\n",
  "test_cases": "import pytest\nimport time\nfrom solution import rate_limit\n\ndef test_rate_limit_allows_within_limit():\n    @rate_limit(max_calls=3, period=60)\n    def f(): return 'ok'\n    assert f() == 'ok'\n    assert f() == 'ok'\n    assert f() == 'ok'\n\ndef test_rate_limit_blocks_when_exceeded():\n    @rate_limit(max_calls=2, period=60)\n    def f(): return 'ok'\n    f(); f()\n    with pytest.raises(RuntimeError):\n        f()\n\ndef test_rate_limit_resets_after_period():\n    @rate_limit(max_calls=1, period=1)\n    def f(): return 'ok'\n    assert f() == 'ok'\n    with pytest.raises(RuntimeError):\n        f()\n    time.sleep(1.1)\n    assert f() == 'ok'\n"
}
```

**MVP 扩展字段说明：**
- `problem_statement` 为 MVP 阶段预置的题目说明文本（数据文件，非代码硬编码）
- 严格匹配 Demo设计.md §1.1「采用预置 Markdown 文件及 JSON 元数据」允许的预置数据形式
- 生产环境可由 Generator Agent 调用 LLM 动态生成替换此字段

### 6.4 默认用户画像 (learner_profile) — 严格匹配 最终成品设计.md §4.3

```json
{
  "user_id": "default_user",
  "current_language": "python",
  "mastered_nodes": ["python.basics.syntax", "python.basics.closure"],
  "failed_nodes_queue": ["python.advanced.decorator"],
  "preferred_learning_style": "practical_first",
  "implicit_metrics": {
    "average_time_per_exercise_sec": 420,
    "first_pass_rate": 0.75
  }
}
```

---

## 7. 统一响应规范

### 7.1 成功响应
所有成功响应必须包含 `status: "success"` 字段。

### 7.2 错误响应
所有错误响应必须遵循：
```json
{
  "status": "error",
  "message": "人类可读错误描述",
  "code": 500
}
```

### 7.3 状态机流转
```
TeachMode --(go_to_practice)--> PracticeMode
PracticeMode --(passed=true)--> EcosystemMode
PracticeMode --(passed=false)--> PracticeMode (重试)
EcosystemMode --(next_node)--> TeachMode (新节点)
```

---

## 8. app/requirements.txt 依赖清单

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pytest>=7.4.0
requests>=2.31.0
```

---

## 9. 验收清单 (Acceptance Checklist)

- [ ] FastAPI 应用启动无错误（`uvicorn main:app --reload`）
- [ ] 4 个端点返回符合 Pydantic 模型的响应
- [ ] `schemas/seed_data.json` 包含装饰器知识元 + 种子题库 + 默认画像
- [ ] CORS 中间件正确配置
- [ ] 静态文件 `/static` 可访问
- [ ] 全局异常处理器返回结构化错误 JSON
- [ ] 错误响应不暴露原始 Traceback

---

## 10. 依赖关系

- **上游依赖**：无（本规范为后端基础）
- **下游消费**：
  - DOC-02（沙盒引擎）：`/api/generate_exercise` 和 `/api/submit_code` 调用 sandbox
  - DOC-03（Agent 工作流）：`/api/generate_exercise` 调用 Generator/Validator
  - DOC-04（前端）：所有 4 个端点被前端 fetch 调用
