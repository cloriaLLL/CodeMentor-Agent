# CodeMentor Agent — AI 编程教学智能体

![Python](https://img.shields.io/badge/Python-3.12-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal) ![React](https://img.shields.io/badge/React-19-61dafb) ![TypeScript](https://img.shields.io/badge/TypeScript-6-blue) ![SQLite](https://img.shields.io/badge/SQLite-WAL-orange) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

> 对话驱动的自适应编程学习智能体 —— 以"三层教学结构 + 四步教学节奏"为核心教学法，将知识讲解、代码练习、沙箱判题、学习进度追踪整合为一体化体验。

> 📖 本文档为**开发指南**，面向本地使用者介绍如何配置环境与运行项目。比赛面向的项目总介绍见 [项目介绍](docs/项目介绍.md)。详细介绍见 [PROJECT_REPORT](docs/PROJECT_REPORT.md)

---

## 📖 项目简介

CodeMentor Agent 是一个面向编程学习者的 **AI 智能导师系统**，解决传统编程教育"资源碎片化、学习路径不可控、练习反馈缺失闭环"的痛点：

- 🎓 **结构化教学**：三层教学结构（对话 → 教学 → 推进）+ 四步教学节奏（实例 → 概念 → 溯源 → 练习），避免 AI "一问一答"式碎片化答疑
- 🧪 **即时代码练习**：内置多语言安全沙箱，学完即练、提交即判，支持 Python / JavaScript / Bash / Java / C# 五种语言
- 🤖 **Agent 驱动**：OrchestratorAgent 主控状态机 + ExerciseGeneratorAgent 出题 + ExerciseEvaluator 评估，形成"学 → 练 → 判 → 反馈"完整闭环
- 💾 **学习进度持久化**：SQLite 存储学习会话、对话历史、提交记录，支持断点续学
- 🔓 **零成本启动**：默认接入智谱 GLM-4-Flash 永久免费模型；支持 Ollama 完全离线部署

---

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18.0+
- Python 包管理器：`pip`（Python 自带）或 [uv](https://docs.astral.sh/uv/)（推荐，更快）—— 任选其一

### 后端启动

提供两种依赖安装方式，任选其一。依赖清单位于 `app/requirements.txt`。

**方式一：venv + pip（标准方式）**

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate                   # Windows PowerShell
# source .venv/bin/activate              # Mac/Linux

# 2. 安装依赖
pip install -r app/requirements.txt

# 3. 配置环境变量
copy .env.example .env                   # Windows
# cp .env.example .env                   # Mac/Linux
# 编辑 .env 填入 ZHIPU_API_KEY（注册地址：https://bigmodel.cn）

# 4. 启动服务（默认 8000 端口）
python main.py
```

**方式二：uv（更快的 Python 包管理器，推荐）**

```bash
# 1. 安装依赖（uv 会自动创建并管理虚拟环境，无需手动 venv）
uv pip install -r app/requirements.txt

# 2. 配置环境变量（同方式一）
copy .env.example .env                   # Windows
# cp .env.example .env                   # Mac/Linux

# 3. 启动服务
uv run python main.py
# 或：uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev    # 默认 5173 端口，自动代理 /api 到后端 8000
```

### 生产部署

```bash
# 构建前端静态文件
cd frontend && npm run build

# 后端自动托管前端 dist/，访问 http://localhost:8000/ 即可使用完整应用
python main.py
# uv run python main.py    # uv 方式
```

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────┐
│              前端 (React 19 + TypeScript + Vite)          │
│     对话教学区 / 代码练习区 / 笔记本模式 / 毛玻璃模糊 UI     │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP REST + SSE 流式
┌──────────────────────────▼──────────────────────────────┐
│              后端 (FastAPI + Python 3.12)                 │
│   teach / chat / learn / exercise / conversation / ...   │
└──────┬───────────────────┬──────────────────┬───────────┘
       │                   │                  │
┌──────▼──────┐  ┌─────────▼─────────┐  ┌────▼──────────┐
│ Agent 系统   │  │   沙箱执行引擎     │  │  MiniLang     │
│ Orchestrator│  │ 5 语言代码运行     │  │  编译器       │
│ Generator   │  │ 安全检查 + 隔离    │  │  AST 白名单   │
│ Evaluator   │  │ pytest 判题       │  │  代码生成     │
└──────┬──────┘  └───────────────────┘  └───────────────┘
       │
┌──────▼──────────────────────────────────────────────────┐
│  LLM 层 (智谱 GLM-4-Flash / Ollama / Mock 降级)          │
│  prompts/ 外置模板（@lru_cache 缓存）                     │
└─────────────────────────────────────────────────────────┘
       │
┌──────▼──────────┐
│  SQLite (WAL)   │
│ 会话/对话/进度   │
└─────────────────┘
```

---

## 📦 项目结构

```
CodeMentor Agent/
├── README.md                    # 开发指南（本文档：本地运行说明）
├── main.py                      # 应用入口
├── .env / .env.example          # 环境配置（.env 在 .gitignore 中）
├── pytest.ini                   # 测试配置
│
├── agents/                      # Agent 系统
│   ├── orchestrator.py          #   主控 Agent（三层四步状态机）
│   ├── exercise_generator.py    #   出题 Agent（4 种题型）
│   ├── exercise_evaluator/      #   评估 Agent（子包：models/quality/ai_feedback/core）
│   ├── llm_client.py            #   LLM 客户端（智谱/Ollama/Mock 三级降级）
│   ├── sandbox.py               #   沙箱执行入口
│   ├── sandbox_security.py      #   安全检查（5 语言 forbidden 规则）
│   ├── sandbox_isolation.py     #   隔离执行器（Docker 首选 + 进程树降级）
│   ├── sandbox_runtime.py       #   多语言运行时注册表
│   └── ...
│
├── app/                         # FastAPI 后端
│   ├── requirements.txt          #   Python 依赖清单
│   ├── api/                     #   路由模块
│   │   ├── teach.py             #     /api/teach — 教学模式
│   │   ├── chat.py              #     /api/chat — 对话（含 SSE 流式）
│   │   ├── learn.py             #     /api/learn — 学习会话管理
│   │   ├── exercise.py          #     /api/exercise — 练习生成与评估
│   │   ├── conversation.py      #     /api/conversation — 对话存储
│   │   ├── compiler.py          #     /api/compiler — MiniLang 编译器
│   │   ├── llm.py               #     /api/llm — LLM 模型管理
│   │   └── health.py            #     /health — 健康检查
│   ├── core/                    #   核心设施
│   │   ├── config.py            #     配置（pydantic-settings 读 .env）
│   │   ├── container.py         #     依赖注入容器
│   │   ├── app_factory.py       #     FastAPI 工厂
│   │   ├── database.py          #     SQLite 数据库
│   │   ├── exceptions.py        #     异常体系
│   │   └── logger.py            #     structlog 日志
│   ├── services/                #   业务逻辑层
│   └── schemas/                 #   Pydantic 请求/响应模型
│
├── compiler/                    # MiniLang 编译器（词法→语法→代码生成→缓存）
├── frontend/                    # React 前端（见下方"前端开发"）
├── prompts/                     # 外置 prompt 模板（8 个 .txt，@lru_cache 加载）
├── schemas/                     # seed_data.json（知识图谱种子数据）
├── static/                      # 静态文件
├── data/                        # SQLite 数据库文件
│
├── docs/                        # 📚 项目文档
│   ├── 项目介绍.md              #   比赛文稿（项目总介绍）
│   ├── specs/                   #   技术规范（DOC-01 ~ DOC-05）
│   ├── design/                  #   设计文档
│   ├── reports/                 #   项目报告
│   └── plans/                   #   开发计划
│
└── tests/                       # 🧪 测试
    ├── conftest.py              #   全局 fixture（Mock LLM + TestClient）
    ├── sandbox/                 #   沙箱测试（4 个）
    ├── compiler/                #   编译器测试（3 个）
    └── api/                     #   API 路由测试（2 个）
```

---

## 📚 文档目录

### 总览

| 文档 | 说明 |
|------|------|
| [项目介绍（比赛文稿）](docs/项目介绍.md) | 比赛面向的项目总介绍：项目简介、核心创新、使用方法、技术架构、未来规划、已知局限 |

### 设计文档（docs/design/）

| 文档 | 说明 |
|------|------|
| [最终成品设计](docs/design/最终成品设计.md) | 顶层架构与工程规范 |
| [Demo 设计](docs/design/Demo设计.md) | 演示界面设计与交互流程 |
| [比赛说明](docs/design/比赛说明.md) | 参赛要求与评分标准 |

### 技术规范（docs/specs/）

| 文档 | 说明 |
|------|------|
| [DOC-01 后端路由与数据模型](docs/specs/DOC-01-Backend_Routes_and_Data_Schemas.md) | API 端点结构与 Pydantic Schema |
| [DOC-02 沙箱执行引擎](docs/specs/DOC-02-Sandbox_Executor_Engine.md) | 多语言代码执行与安全隔离设计 |
| [DOC-03 Agent 工作流与 Prompt](docs/specs/DOC-03-Agentic_Workflow_and_Prompts.md) | 智能体交互与 prompt 模板设计 |
| [DOC-04 前端分屏工作区](docs/specs/DOC-04-Frontend_SplitScreen_Workspace.md) | UI 布局与交互设计 |
| [DOC-05 编译器集成](docs/specs/DOC-05-Compiler_Integration.md) | MiniLang 编译器与 IDE 语言服务 |

### 项目报告（docs/reports/）

| 文档 | 说明 |
|------|------|
| [项目总结报告](docs/reports/PROJECT_REPORT.md) | 项目全貌：背景、架构、功能、历程、性能指标、未来规划 |

### 开发计划（docs/plans/）

| 文档 | 说明 |
|------|------|
| [P1 架构重构方案](docs/plans/P1架构重构方案.md) | P1 阶段架构重构的整体方案 |
| [P1 续作-子任务 A 收尾与 C 实施](docs/plans/P1续作-子任务A收尾与C实施.md) | P1 续作：子任务 A 收尾与子任务 C（prompt 外置）实施 |
| [对话存储架构重构](docs/plans/对话存储架构重构.md) | 对话存储层的架构重构方案 |

---

## 🔧 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 运行时 |
| FastAPI | 0.115+ | Web 框架 |
| pydantic | 2.9+ | 数据验证 |
| pydantic-settings | 2.6+ | 配置管理（读 `.env`） |
| openai | 1.50+ | LLM 客户端（智谱 GLM-4 兼容 OpenAI API） |
| structlog | 24.4+ | 结构化日志 |
| SQLite | — | 数据库（WAL 模式） |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19 | UI 框架 |
| TypeScript | 6 | 类型安全 |
| Vite | 8 | 构建工具 |
| Tailwind CSS | v4 | 原子化样式（`@theme` 自定义设计令牌） |
| react-markdown | 10 | Markdown 渲染 |
| remark-gfm + rehype-highlight | — | GFM 语法 + 代码高亮 |
| lucide-react | — | 图标库 |

---

## 🎨 前端开发

### 核心特性

- **双栏分屏工作区**：左侧对话教学 + 右侧代码练习
- **SSE 流式输出**：逐字显示 AI 回复，10s 心跳保活
- **毛玻璃模糊设计系统**：渐进增强（Tier 0 `backdrop-filter` / Tier 1 SVG 折射），尊重 `prefers-reduced-motion`
- **笔记本模式**：章节式知识管理，支持父-子对话结构
- **localStorage 持久化**：会话数据自动保存（500ms 防抖）
- **键盘快捷键**：`Ctrl+N` 新建对话、`Ctrl+Shift+N` 新建笔记本、`Ctrl+B` 切换侧边栏
- **PWA 支持**：可安装为桌面应用

### 前端架构

```text
frontend/src/
├── App.tsx                  # 根组件
├── main.tsx                 # 入口
├── index.css                # Tailwind + 设计令牌 + 毛玻璃模糊样式
├── components/
│   ├── chat/                # 对话区（ChatArea, MessageBubble, ChatInput, WelcomeScreen）
│   ├── exercise/            # 练习区（ExercisePanel, CodeEditor, ChoiceQuestion, ResultFeedback）
│   ├── layout/              # 布局（TopBar, Sidebar, ChapterBar）
│   └── ui/                  # UI 基础组件（button, liquid-glass-card）
├── contexts/                # 全局状态（ChatContext, ExerciseContext）
├── hooks/                   # 自定义 Hooks（useExerciseLauncher）
├── lib/                     # 工具函数（exercise-api, utils）
└── types/                   # 类型定义
```

### 开发命令

```bash
cd frontend
npm install          # 安装依赖
npm run dev          # 开发模式（5173 端口）
npm run build        # 生产构建（输出到 dist/）
npm run preview      # 预览构建产物
npm run lint         # 代码检查（oxlint）
```

### 与后端联调

开发模式下，前端运行在 5173 端口，Vite 自动将 `/api` 请求代理到后端 8000 端口。生产构建后，`dist/` 由后端 FastAPI 托管（`app_factory._configure_static_files` 自动挂载），访问 `http://localhost:8000/` 即可使用完整应用。

---

## 🔒 安全说明

- **API Key 管理**：密钥存储在 `.env` 文件中（已加入 `.gitignore`，不会进入版本控制）。`.env.example` 提供空值模板。运行时通过 `pydantic-settings` 从 `.env` 加载到环境变量，代码中不硬编码任何密钥。
- **沙箱安全**：用户代码在隔离环境中执行（Docker 容器隔离首选，无 Docker 时自动降级为进程树隔离），经过 5 层安全检查（输入验证 → AST 白名单 → forbidden 模式匹配 → 资源限制 → 执行隔离）。安装 Docker 后沙箱会自动检测并优先使用容器级隔离（`--network=none` + 内存/CPU/进程数限制）。

---

## 🧪 测试

```bash
# 运行全部测试（conftest.py 自动 Mock LLM，无需真实 API Key）
pytest tests/ -q                         # 方式一：直接运行
# uv run pytest tests/ -q               # 方式二：uv run（无需手动激活虚拟环境）

# 运行特定模块测试
pytest tests/sandbox/ -q                 # 沙箱测试
pytest tests/compiler/ -q                # 编译器测试
pytest tests/api/ -q                     # API 路由测试
```

---

## 📝 License

MIT © 2026 CodeMentor Agent
